"""Contratos de jobs. O lote estrutural deixa o subconjunto prudencial vazio."""

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
    operation_row_count: int
    guarantee_row_count: int
    multi_mitigator_operation_count: int
    pending_exposure_count: int
    pending_balance: str
    calculated_exposure_count: int
    coverage_ratio: str
    calculated_subset_rwa: str | None
    calculated_subset_pr_contribution: str | None
    status_counts: dict[str, int]


class JobIssuePage(StrictAPIModel):
    job_id: str
    offset: int
    limit: int
    total: int
    issues: list[ValidationIssue]
