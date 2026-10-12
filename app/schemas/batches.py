"""Contratos de jobs de validação, sem resultado prudencial."""

from typing import Literal

from app.core.enums import JobStatus
from app.schemas.common import StrictAPIModel, ValidationIssue


class JobAccepted(StrictAPIModel):
    job_id: str
    status: Literal[JobStatus.PENDING]


class JobStatusResponse(StrictAPIModel):
    job_id: str
    status: JobStatus
    schema_version: str
    calculation_mode: str
    submitted_at: str
    started_at: str | None
    finished_at: str | None
    total_rows: int | None
    processed_rows: int
    operation_count: int | None
    exposure_count: int | None
    mitigator_count: int | None
    issue_count: int
    balance_total: str | None


class BatchSummary(StrictAPIModel):
    operation_count: int
    exposure_count: int
    mitigator_count: int
    balance_total: str
    issue_count: int
    complete_regulatory_coverage: Literal[False]


class JobIssuePage(StrictAPIModel):
    job_id: str
    offset: int
    limit: int
    total: int
    issues: list[ValidationIssue]
