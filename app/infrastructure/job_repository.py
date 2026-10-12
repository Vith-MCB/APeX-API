"""Estados de jobs. A carteira permanece em Parquet, não no SQLite."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.enums import JobStatus
from app.infrastructure.sqlite_db import connect, initialize_db


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    status: JobStatus
    schema_version: str
    calculation_mode: str
    reference_date: str
    context_json: str
    input_sha256: str
    submitted_at: str
    started_at: str | None
    finished_at: str | None
    heartbeat_at: str | None
    worker_id: str | None
    cancel_requested: bool
    total_rows: int | None
    processed_rows: int
    operation_count: int | None
    exposure_count: int | None
    mitigator_count: int | None
    issue_count: int
    balance_total: str | None
    error_message: str | None


class JobRepository:
    def __init__(self, database: Path) -> None:
        self.database = database
        initialize_db(database)

    def create_job(
        self,
        *,
        job_id: str,
        schema_version: str,
        calculation_mode: str,
        reference_date: str,
        context_json: str,
        input_sha256: str,
        total_rows: int,
    ) -> JobRecord:
        submitted_at = _now()
        with connect(self.database) as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, status, schema_version, calculation_mode, reference_date,
                    context_json, input_sha256, submitted_at, total_rows
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    JobStatus.PENDING,
                    schema_version,
                    calculation_mode,
                    reference_date,
                    context_json,
                    input_sha256,
                    submitted_at,
                    total_rows,
                ),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> JobRecord | None:
        with connect(self.database) as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return None if row is None else _record(row)

    def claim_next_job(self, worker_id: str) -> JobRecord | None:
        now = _now()
        with connect(self.database) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT job_id FROM jobs
                WHERE status = ?
                ORDER BY submitted_at
                LIMIT 1
                """,
                (JobStatus.PENDING,),
            ).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return None
            updated = connection.execute(
                """
                UPDATE jobs
                SET status = ?, worker_id = ?, started_at = ?, heartbeat_at = ?
                WHERE job_id = ? AND status = ?
                """,
                (
                    JobStatus.RUNNING,
                    worker_id,
                    now,
                    now,
                    row["job_id"],
                    JobStatus.PENDING,
                ),
            )
            connection.execute("COMMIT")
            if updated.rowcount != 1:
                return None
            job_id = row["job_id"]
        return self.get_job(job_id)

    def update_progress(self, job_id: str, *, processed_delta: int) -> None:
        with connect(self.database) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET processed_rows = processed_rows + ?, heartbeat_at = ?
                WHERE job_id = ? AND status = ?
                """,
                (processed_delta, _now(), job_id, JobStatus.RUNNING),
            )

    def request_cancel(self, job_id: str) -> JobRecord | None:
        with connect(self.database) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET cancel_requested = 1,
                    status = CASE WHEN status = ? THEN ? ELSE status END,
                    finished_at = CASE WHEN status = ? THEN ? ELSE finished_at END
                WHERE job_id = ? AND status IN (?, ?)
                """,
                (
                    JobStatus.PENDING,
                    JobStatus.CANCELLED,
                    JobStatus.PENDING,
                    _now(),
                    job_id,
                    JobStatus.PENDING,
                    JobStatus.RUNNING,
                ),
            )
        return self.get_job(job_id)

    def finish_job(
        self,
        job_id: str,
        status: JobStatus,
        *,
        operation_count: int | None = None,
        exposure_count: int | None = None,
        mitigator_count: int | None = None,
        issue_count: int | None = None,
        balance_total: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with connect(self.database) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, finished_at = ?, operation_count = COALESCE(?, operation_count),
                    exposure_count = COALESCE(?, exposure_count),
                    mitigator_count = COALESCE(?, mitigator_count),
                    issue_count = COALESCE(?, issue_count),
                    balance_total = COALESCE(?, balance_total),
                    error_message = ?
                WHERE job_id = ?
                """,
                (
                    status,
                    _now(),
                    operation_count,
                    exposure_count,
                    mitigator_count,
                    issue_count,
                    balance_total,
                    error_message,
                    job_id,
                ),
            )

    def delete_job(self, job_id: str) -> JobStatus | None:
        job = self.get_job(job_id)
        if job is None:
            return None
        if job.status is JobStatus.RUNNING:
            return job.status
        with connect(self.database) as connection:
            connection.execute("DELETE FROM jobs WHERE job_id = ? AND status != ?", (job_id, JobStatus.RUNNING))
        return job.status

    def running_jobs(self) -> list[JobRecord]:
        with connect(self.database) as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE status = ?",
                (JobStatus.RUNNING,),
            ).fetchall()
        return [_record(row) for row in rows]


def is_stale(job: JobRecord, *, timeout_seconds: int, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    if job.heartbeat_at is None:
        return True
    heartbeat = datetime.fromisoformat(job.heartbeat_at)
    return heartbeat < current - timedelta(seconds=timeout_seconds)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(row) -> JobRecord:
    return JobRecord(
        job_id=row["job_id"],
        status=JobStatus(row["status"]),
        schema_version=row["schema_version"],
        calculation_mode=row["calculation_mode"],
        reference_date=row["reference_date"],
        context_json=row["context_json"],
        input_sha256=row["input_sha256"],
        submitted_at=row["submitted_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        heartbeat_at=row["heartbeat_at"],
        worker_id=row["worker_id"],
        cancel_requested=bool(row["cancel_requested"]),
        total_rows=row["total_rows"],
        processed_rows=row["processed_rows"],
        operation_count=row["operation_count"],
        exposure_count=row["exposure_count"],
        mitigator_count=row["mitigator_count"],
        issue_count=row["issue_count"],
        balance_total=row["balance_total"],
        error_message=row["error_message"],
    )
