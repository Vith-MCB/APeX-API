"""Executa um job de validação e só então publica a saída."""

import json

from app.core.config import Settings, get_settings
from app.core.enums import JobStatus
from app.core.money import quantize_money
from app.ingestion.combined_normalizer import normalize_combined, operation_balance_total
from app.ingestion.parquet_reader import ParquetReadError, inspect_parquet
from app.ingestion.relationship_validator import validate_links
from app.infrastructure.file_store import FileStore
from app.infrastructure.job_repository import JobRecord, JobRepository, is_stale
from app.infrastructure.manifest import write_manifest
from app.reporting.exporter import write_validation_summary
from app.reporting.issues import export_issues
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
) -> None:
    try:
        source = store.input_file(job.job_id)
        inspect_parquet(source, max_bytes=settings.max_upload_bytes)

        def on_batch(batch) -> None:
            check_cancel(repository, job.job_id)
            repository.update_progress(job.job_id, processed_delta=batch.num_rows)

        canonical = validate_links(normalize_combined(source, on_batch=on_batch))
        check_cancel(repository, job.job_id)
        balance = quantize_money(operation_balance_total(canonical.operations), 2)
        summary = {
            "operation_count": len(canonical.operations),
            "exposure_count": len(canonical.exposures),
            "mitigator_count": len(canonical.mitigators),
            "balance_total": f"{balance:.2f}",
            "issue_count": len(canonical.issues),
            "complete_regulatory_coverage": False,
        }
        work = store.work_directory(job.job_id)
        export_issues(work / "issues.parquet", canonical.issues)
        write_validation_summary(work / "summary.json", summary)
        write_manifest(
            work / "manifest.json",
            {
                "job_id": job.job_id,
                "schema_version": job.schema_version,
                "input_sha256": job.input_sha256,
                "artifacts": ["issues.parquet", "summary.json", "manifest.json"],
                "complete_regulatory_coverage": False,
            },
        )
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
