"""Mede validação estrutural e exportação de lotes sintéticos.

O tempo de gerar o Parquet não entra na vazão. O experimento não executa o
cálculo didático. Cada medição de processamento nasce em um processo novo.
"""

import argparse
import json
import platform
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SIZES = (1_000, 10_000, 50_000, 100_000)
MILLION = 1_000_000
DEFAULT_UPLOAD_BYTES = 200 * 1024 * 1024
OUTPUT_NAMES = (
    "results.parquet",
    "tranches.parquet",
    "issues.parquet",
    "trace.parquet",
    "summary.json",
    "manifest.json",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark estrutural da APeX-API")
    parser.add_argument("--phase", choices=("generate", "process"))
    parser.add_argument("--rows", type=int)
    parser.add_argument("--parquet", type=Path)
    parser.add_argument("--sizes", default=",".join(str(size) for size in DEFAULT_SIZES))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--no-million", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/benchmarks/results.json"))
    args = parser.parse_args(argv)

    if args.phase == "generate":
        print(json.dumps(_generate(args.rows, args.parquet)))
        return 0
    if args.phase == "process":
        print(json.dumps(_process(args.parquet, args.rows)))
        return 0

    sizes = [int(item) for item in args.sizes.split(",") if item]
    runs: list[dict[str, object]] = []
    for size in sizes:
        for repeat in range(args.repeats):
            runs.append(_orchestrate(size, repeat, exploratory=False))
    if not args.no_million:
        runs.append(_orchestrate(MILLION, 0, exploratory=True))

    payload = {
        "workload": "structural_validation_and_export",
        "didactic_calculation": False,
        "environment": _environment(),
        "runs": runs,
        "summaries": _summaries(runs),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if all("error" not in run for run in runs if not run.get("exploratory")) else 1


def _orchestrate(size: int, repeat: int, *, exploratory: bool) -> dict[str, object]:
    work = Path(tempfile.mkdtemp(prefix="apex-bench-"))
    parquet = work / "input.parquet"
    timeout = _timeout(size)
    try:
        generated = _invoke("generate", size, parquet, timeout)
        if "error" in generated:
            return _failure(size, repeat, exploratory, "generate", generated["error"])
        processed = _invoke("process", size, parquet, timeout)
        if "error" in processed and "total_seconds" not in processed:
            return _failure(size, repeat, exploratory, "process", processed["error"])
        return {
            "rows": size,
            "repeat": repeat,
            "exploratory": exploratory,
            **generated,
            **processed,
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _invoke(phase: str, rows: int, parquet: Path, timeout: int) -> dict[str, object]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--phase",
        phase,
        "--rows",
        str(rows),
        "--parquet",
        str(parquet),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"tempo esgotado depois de {timeout} segundos"}
    if completed.returncode != 0 and not completed.stdout.strip():
        detail = completed.stderr.strip() or "fase sem saída"
        return {"error": detail[-1500:]}
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = completed.stderr.strip() or completed.stdout.strip()
        return {"error": detail[-1500:] or "saída inválida"}


def _generate(rows: int | None, parquet: Path | None) -> dict[str, object]:
    if rows is None or parquet is None:
        raise SystemExit("generate exige --rows e --parquet")
    started = time.perf_counter()
    write_synthetic_operations(rows, parquet)
    return {
        "generation_seconds": time.perf_counter() - started,
        "input_bytes": parquet.stat().st_size,
    }


def _process(parquet: Path | None, rows: int | None) -> dict[str, object]:
    if parquet is None or rows is None:
        raise SystemExit("process exige --rows e --parquet")
    from app.core.config import Settings
    from app.infrastructure.file_store import FileStore
    from app.infrastructure.job_repository import JobRepository
    from app.ingestion.parquet_reader import inspect_parquet
    from app.worker.job_runner import run_job

    data_dir = Path(tempfile.mkdtemp(prefix="apex-job-"))
    try:
        input_bytes = parquet.stat().st_size
        settings = Settings(
            data_dir=data_dir,
            max_upload_bytes=max(DEFAULT_UPLOAD_BYTES, input_bytes + 1),
            heartbeat_timeout_seconds=3600,
        )
        job_id = str(uuid.uuid4())
        store = FileStore(settings.data_dir)
        with parquet.open("rb") as handle:
            _stored, digest = store.save_upload(
                handle,
                job_id,
                max_bytes=settings.max_upload_bytes,
            )
        inspected = inspect_parquet(
            store.input_file(job_id),
            max_bytes=settings.max_upload_bytes,
        )
        context = (ROOT / "examples/calculation_context.json").read_text(encoding="utf-8")
        repository = JobRepository(settings.database_path)
        repository.create_job(
            job_id=job_id,
            schema_version="combined_v1",
            calculation_mode="VALIDATION_ONLY",
            reference_date="2026-09-30",
            context_json=context,
            input_sha256=digest,
            total_rows=inspected.num_rows,
        )
        job = repository.claim_next_job("benchmark")
        if job is None:
            return {"error": "job não foi reservado"}
        stages: dict[str, float] = {}
        started = time.perf_counter()
        run_job(job, repository, store, settings, stage_seconds=stages)
        total = time.perf_counter() - started
        finished = repository.get_job(job_id)
        output = store.output_directory(job_id)
        summary_path = output / "summary.json"
        summary = (
            json.loads(summary_path.read_text(encoding="utf-8"))
            if summary_path.is_file()
            else {}
        )
        rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {
            "status": None if finished is None else str(finished.status),
            "total_seconds": total,
            "validation_seconds": stages.get("validation_seconds"),
            "export_seconds": stages.get("export_seconds"),
            "rows_processed": inspected.num_rows,
            "rows_per_second": None if total == 0 else inspected.num_rows / total,
            "rss_kib": rss_kib,
            "rss_mib": rss_kib / 1024,
            "output_bytes": {
                name: (output / name).stat().st_size if (output / name).is_file() else None
                for name in OUTPUT_NAMES
            },
            "calculated_subset_rwa": summary.get("calculated_subset_rwa", "ausente"),
            "exceeds_default_upload_limit": input_bytes > DEFAULT_UPLOAD_BYTES,
        }
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


def write_synthetic_operations(row_count: int, destination: Path) -> None:
    import pyarrow.parquet as pq

    from app.ingestion.schemas import get_arrow_schema

    schema = get_arrow_schema("combined_v1")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with pq.ParquetWriter(destination, schema, compression="snappy") as writer:
        produced = 0
        while produced < row_count:
            count = min(65_536, row_count - produced)
            writer.write_batch(_batch(schema, produced, count))
            produced += count


def _batch(schema, start: int, count: int):
    import pyarrow as pa

    columns = [_column(field, start, count) for field in schema]
    return pa.RecordBatch.from_arrays(columns, schema=schema)


def _column(field, start: int, count: int):
    import pyarrow as pa

    name = field.name
    if name == "record_type":
        return pa.array(["OPERATION"] * count, type=field.type)
    if name == "row_id":
        return pa.array([f"r{index}" for index in range(start, start + count)], type=field.type)
    if name == "operation_id":
        return pa.array(
            [f"{index:08d}" for index in range(start, start + count)],
            type=field.type,
        )
    if name == "exposure_id":
        return pa.array(
            [f"EXP-{index}" for index in range(start, start + count)],
            type=field.type,
        )
    if name == "reference_date":
        return pa.array([date(2026, 9, 30)] * count, type=field.type)
    if name == "product_type":
        return pa.array(["SYNTHETIC_CREDIT"] * count, type=field.type)
    if name == "balance_amount":
        return pa.array([Decimal("1.00")] * count, type=field.type)
    if name == "currency":
        return pa.array(["BRL"] * count, type=field.type)
    if name in {"is_off_balance", "has_guarantee"}:
        return pa.array([False] * count, type=field.type)
    return pa.nulls(count, type=field.type)


def _environment() -> dict[str, str]:
    import pyarrow as pa

    cpu = "indisponível"
    memory = "indisponível"
    cpuinfo = Path("/proc/cpuinfo")
    meminfo = Path("/proc/meminfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal"):
                memory = line.split(":", 1)[1].strip()
                break
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu": cpu,
        "memory_total": memory,
        "pyarrow": pa.__version__,
    }


def _summaries(runs: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[int, list[dict[str, object]]] = {}
    for run in runs:
        if "error" in run or "total_seconds" not in run:
            continue
        grouped.setdefault(int(run["rows"]), []).append(run)
    summaries = []
    for rows, samples in grouped.items():
        summaries.append(
            {
                "rows": rows,
                "repeats": len(samples),
                "exploratory": bool(samples[0].get("exploratory")),
                "median_total_seconds": statistics.median(
                    [float(sample["total_seconds"]) for sample in samples]
                ),
                "min_total_seconds": min(float(sample["total_seconds"]) for sample in samples),
                "max_total_seconds": max(float(sample["total_seconds"]) for sample in samples),
                "median_validation_seconds": statistics.median(
                    [float(sample["validation_seconds"]) for sample in samples]
                ),
                "median_export_seconds": statistics.median(
                    [float(sample["export_seconds"]) for sample in samples]
                ),
                "median_rows_per_second": statistics.median(
                    [float(sample["rows_per_second"]) for sample in samples]
                ),
                "median_rss_mib": statistics.median(
                    [float(sample["rss_mib"]) for sample in samples]
                ),
                "max_rss_mib": max(float(sample["rss_mib"]) for sample in samples),
                "input_bytes": samples[0]["input_bytes"],
                "output_bytes": samples[0]["output_bytes"],
                "calculated_subset_rwa": samples[0]["calculated_subset_rwa"],
                "exceeds_default_upload_limit": samples[0]["exceeds_default_upload_limit"],
            }
        )
    return summaries


def _failure(
    size: int,
    repeat: int,
    exploratory: bool,
    phase: str,
    error: object,
) -> dict[str, object]:
    return {
        "rows": size,
        "repeat": repeat,
        "exploratory": exploratory,
        "phase": phase,
        "error": error,
    }


def _timeout(size: int) -> int:
    if size >= MILLION:
        return 1800
    if size >= 100_000:
        return 600
    if size >= 50_000:
        return 300
    return 180


if __name__ == "__main__":
    raise SystemExit(main())
