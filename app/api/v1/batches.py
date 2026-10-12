"""Upload e consulta de lotes. O processamento fica no worker."""

import json
from typing import Annotated
from uuid import uuid4

import pyarrow.parquet as pq
from fastapi import APIRouter, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.enums import JobStatus
from app.core.errors import PublicAPIError
from app.infrastructure.file_store import FileStore, UnsafePath
from app.infrastructure.job_repository import JobRecord, JobRepository
from app.ingestion.parquet_reader import ParquetReadError, inspect_parquet
from app.schemas.batches import BatchSummary, JobAccepted, JobIssuePage, JobStatusResponse
from app.schemas.common import ErrorResponse, ValidationIssue
from app.schemas.context import CalculationContext

router = APIRouter(prefix="/batches", tags=["batches"])
ARTIFACTS = {
    "issues": "issues.parquet",
    "summary": "summary.json",
    "manifest": "manifest.json",
}
MEDIA_TYPES = {
    "issues": "application/vnd.apache.parquet",
    "summary": "application/json",
    "manifest": "application/json",
}


def _repository() -> JobRepository:
    return JobRepository(get_settings().database_path)


def _store() -> FileStore:
    return FileStore(get_settings().data_dir)


def _status(job: JobRecord) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        schema_version=job.schema_version,
        calculation_mode=job.calculation_mode,
        submitted_at=job.submitted_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        operation_count=job.operation_count,
        exposure_count=job.exposure_count,
        mitigator_count=job.mitigator_count,
        issue_count=job.issue_count,
        balance_total=job.balance_total,
    )


def _require_job(job_id: str) -> JobRecord:
    try:
        _store().output_directory(job_id)
    except UnsafePath as exc:
        raise PublicAPIError("INVALID_SCHEMA", "job id is not valid", status_code=404) from exc
    job = _repository().get_job(job_id)
    if job is None:
        raise PublicAPIError("INVALID_SCHEMA", "job was not found", status_code=404)
    return job


@router.post("", status_code=202, response_model=JobAccepted, responses={400: {"model": ErrorResponse}})
def create_batch(file: UploadFile, context: Annotated[str, Form()]) -> JobAccepted:
    try:
        parsed = CalculationContext.model_validate_json(context)
    except ValidationError as exc:
        raise PublicAPIError(
            "INVALID_SCHEMA",
            "context does not match the calculation contract",
            status_code=422,
            details=[
                {
                    "loc": [part for part in error.get("loc", ()) if isinstance(part, str | int)],
                    "message": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ],
        ) from exc

    settings = get_settings()
    job_id = str(uuid4())
    store = _store()
    try:
        path, digest = store.save_upload(file.file, job_id, max_bytes=settings.max_upload_bytes)
        inspected = inspect_parquet(path, max_bytes=settings.max_upload_bytes)
    except ParquetReadError as exc:
        store.discard_input(job_id)
        raise PublicAPIError("INVALID_SCHEMA", exc.message, status_code=exc.status_code) from exc
    except Exception as exc:
        store.discard_input(job_id)
        raise PublicAPIError("INVALID_SCHEMA", "upload could not be stored", status_code=400) from exc

    job = _repository().create_job(
        job_id=job_id,
        schema_version=parsed.schema_version.value,
        calculation_mode=parsed.calculation_mode.value,
        reference_date=parsed.reference_date.isoformat(),
        context_json=parsed.model_dump_json(),
        input_sha256=digest,
        total_rows=inspected.num_rows,
    )
    return JobAccepted(job_id=job.job_id, status=JobStatus.PENDING)


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_batch(job_id: str) -> JobStatusResponse:
    return _status(_require_job(job_id))


@router.get("/{job_id}/summary", response_model=BatchSummary)
def get_summary(job_id: str) -> BatchSummary:
    job = _require_job(job_id)
    store = _store()
    if not store.is_published(job.job_id):
        raise PublicAPIError("INVALID_SCHEMA", "job output is not available", status_code=409)
    payload = json.loads(store.artifact_path(job.job_id, "summary.json").read_text(encoding="utf-8"))
    return BatchSummary.model_validate(payload)


@router.get("/{job_id}/errors", response_model=JobIssuePage)
def get_errors(
    job_id: str,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 50,
) -> JobIssuePage:
    job = _require_job(job_id)
    store = _store()
    if not store.is_published(job.job_id):
        raise PublicAPIError("INVALID_SCHEMA", "job output is not available", status_code=409)
    rows = pq.read_table(store.artifact_path(job.job_id, "issues.parquet")).to_pylist()
    page = rows[offset : offset + limit]
    return JobIssuePage(
        job_id=job.job_id,
        offset=offset,
        limit=limit,
        total=len(rows),
        issues=[ValidationIssue.model_validate(row) for row in page],
    )


@router.get("/{job_id}/artifacts/{kind}")
def get_artifact(job_id: str, kind: str) -> FileResponse:
    filename = ARTIFACTS.get(kind)
    if filename is None:
        raise PublicAPIError("INVALID_SCHEMA", "artifact is not available", status_code=404)
    job = _require_job(job_id)
    store = _store()
    if not store.is_published(job.job_id):
        raise PublicAPIError("INVALID_SCHEMA", "job output is not available", status_code=409)
    path = store.artifact_path(job.job_id, filename)
    if not path.is_file():
        raise PublicAPIError("INVALID_SCHEMA", "artifact is not available", status_code=404)
    return FileResponse(path, media_type=MEDIA_TYPES[kind], filename=filename)


@router.post("/{job_id}/cancel", response_model=JobStatusResponse)
def cancel_batch(job_id: str) -> JobStatusResponse:
    _require_job(job_id)
    job = _repository().request_cancel(job_id)
    if job is None:
        raise PublicAPIError("INVALID_SCHEMA", "job was not found", status_code=404)
    return _status(job)


@router.delete("/{job_id}", status_code=204)
def delete_batch(job_id: str) -> Response:
    job = _require_job(job_id)
    if job.status is JobStatus.RUNNING:
        raise PublicAPIError("INVALID_SCHEMA", "running job cannot be deleted", status_code=409)
    status = _repository().delete_job(job_id)
    if status is JobStatus.RUNNING:
        raise PublicAPIError("INVALID_SCHEMA", "running job cannot be deleted", status_code=409)
    store = _store()
    store.discard_input(job_id)
    store.discard_work(job_id)
    store.discard_output(job_id)
    return Response(status_code=204)
