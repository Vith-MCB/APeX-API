"""Executa um job de validação e só então publica a saída."""

import json
import time

from app.core.config import Settings, get_settings
from app.core.enums import JobStatus
from app.core.money import quantize_money
from app.ingestion.combined_normalizer import normalize_combined, operation_balance_total
from app.ingestion.parquet_reader import ParquetReadError, inspect_parquet
from app.ingestion.relationship_validator import validate_links
from app.infrastructure.file_store import FileStore
from app.infrastructure.job_repository import JobRecord, JobRepository, is_stale
from app.reporting.dossier import visible_rules, visible_sources
from app.reporting.exporter import (
    artifact_hashes,
    write_manifest,
    write_results,
    write_summary,
    write_tranches,
    write_traces,
)
from app.reporting.issues import export_issues
from app.reporting.portfolio import aggregate_portfolio, structural_exposure_exports
from app.worker.progress import JobCancelled, check_cancel

WORKER_ID = "local-worker"


def run_once(settings: Settings | None = None) -> bool:
    active = settings or get_settings()
    repository = JobRepository(active.database_path)
    store = FileStore(active.data_dir)
    recover_interrupted_jobs(repository, store, active.heartbeat_timeout_seconds)
    job = repository.claim_next_job(WORKER_ID)
    if job is None:
        return False
    run_job(job, repository, store, active)
    return True


def recover_interrupted_jobs(
    repository: JobRepository,
    store: FileStore,
    timeout_seconds: int,
) -> None:
    for job in repository.running_jobs():
        if not is_stale(job, timeout_seconds=timeout_seconds):
            continue
        if store.is_published(job.job_id):
            try:
                summary = json.loads(
                    store.artifact_path(job.job_id, "summary.json").read_text(encoding="utf-8")
                )
                status = JobStatus.PARTIAL if summary["issue_count"] else JobStatus.COMPLETED
            except (OSError, json.JSONDecodeError, KeyError):
                repository.finish_job(
                    job.job_id,
                    JobStatus.FAILED,
                    error_message="published output is unreadable",
                )
                continue
            repository.finish_job(
                job.job_id,
                status,
                operation_count=summary["operation_count"],
                exposure_count=summary["exposure_count"],
                mitigator_count=summary["mitigator_count"],
                issue_count=summary["issue_count"],
                balance_total=summary["balance_total"],
            )
            continue
        store.discard_work(job.job_id)
        repository.finish_job(job.job_id, JobStatus.INTERRUPTED, error_message="worker heartbeat expired")


def run_job(
    job: JobRecord,
    repository: JobRepository,
    store: FileStore,
    settings: Settings,
    stage_seconds: dict[str, float] | None = None,
) -> None:
    try:
        validation_started = time.perf_counter()
        source = store.input_file(job.job_id)
        inspect_parquet(source, max_bytes=settings.max_upload_bytes)

        def on_batch(batch) -> None:
            check_cancel(repository, job.job_id)
            repository.update_progress(job.job_id, processed_delta=batch.num_rows)

        normalized = normalize_combined(source, on_batch=on_batch)
        canonical = validate_links(normalized)
        _remember(stage_seconds, "validation_seconds", validation_started)
        check_cancel(repository, job.job_id)
        export_started = time.perf_counter()
        context = json.loads(job.context_json)
        results = structural_exposure_exports(
            canonical.operations,
            canonical.mitigators,
            job_id=job.job_id,
            calculation_mode=job.calculation_mode,
            rule_set_version=str(context["rule_set_version"]),
            input_sha256=job.input_sha256,
        )
        balance = quantize_money(operation_balance_total(canonical.operations), 2)
        summary = aggregate_portfolio(
            results,
            operation_row_count=len(canonical.operations),
            guarantee_row_count=len(normalized.mitigators),
            issue_count=len(canonical.issues),
            balance_total=balance,
        )
        work = store.work_directory(job.job_id)
        output_names = [
            "results.parquet",
            "tranches.parquet",
            "issues.parquet",
            "trace.parquet",
            "summary.json",
        ]
        write_results(work / "results.parquet", results)
        write_tranches(work / "tranches.parquet", [])
        export_issues(work / "issues.parquet", canonical.issues)
        write_traces(work / "trace.parquet", [])
        write_summary(work / "summary.json", summary)
        write_manifest(
            work / "manifest.json",
            {
                "job_id": job.job_id,
                "schema_version": job.schema_version,
                "calculation_mode": job.calculation_mode,
                "reference_date": job.reference_date,
                "input_sha256": job.input_sha256,
                "artifact_sha256": artifact_hashes(work, output_names),
                "rules": visible_rules(),
                "sources": visible_sources(),
                "complete_regulatory_coverage": False,
            },
        )
        _remember(stage_seconds, "export_seconds", export_started)
        store.publish(job.job_id)
        repository.finish_job(
            job.job_id,
            JobStatus.PARTIAL if canonical.issues else JobStatus.COMPLETED,
            operation_count=summary["operation_count"],
            exposure_count=summary["exposure_count"],
            mitigator_count=summary["mitigator_count"],
            issue_count=summary["issue_count"],
            balance_total=summary["balance_total"],
        )
    except JobCancelled:
        store.discard_work(job.job_id)
        repository.finish_job(job.job_id, JobStatus.CANCELLED)
    except ParquetReadError:
        store.discard_work(job.job_id)
        repository.finish_job(job.job_id, JobStatus.FAILED, error_message="input parquet is not readable")
    except Exception:
        store.discard_work(job.job_id)
        repository.finish_job(job.job_id, JobStatus.FAILED, error_message="job failed before publishing output")


def _remember(stage_seconds: dict[str, float] | None, name: str, started: float) -> None:
    if stage_seconds is None:
        return
    stage_seconds[name] = time.perf_counter() - started
