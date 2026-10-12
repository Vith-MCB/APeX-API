"""Vínculos entre operações e garantias, sem calcular cobertura."""

from dataclasses import dataclass, field

from app.core.enums import IssueCode
from app.domain.models.exposure import Exposure, Operation
from app.domain.models.mitigator import Mitigator
from app.ingestion.combined_normalizer import NormalizedPortfolio
from app.schemas.common import ValidationIssue


@dataclass
class CanonicalPortfolio:
    operations: list[Operation] = field(default_factory=list)
    exposures: list[Exposure] = field(default_factory=list)
    mitigators: list[Mitigator] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def validate_links(portfolio: NormalizedPortfolio) -> CanonicalPortfolio:
    issues = list(portfolio.issues)
    seen_row_ids: set[str] = set()
    operations: list[Operation] = []
    operation_ids: set[str] = set()
    exposure_ids: set[str] = set()
    mitigators: list[Mitigator] = []

    for operation in portfolio.operations:
        if _row_already_seen(operation.row_id, seen_row_ids, issues):
            continue
        if operation.operation_id in operation_ids or operation.exposure_id in exposure_ids:
            existing = next(
                (
                    item
                    for item in operations
                    if item.operation_id == operation.operation_id
                ),
                None,
            )
            message = (
                "duplicate operation_id with a different balance"
                if existing is not None and existing.balance_amount != operation.balance_amount
                else "duplicate operation_id or exposure_id"
            )
            issues.append(
                ValidationIssue(
                    code=IssueCode.DUPLICATE_OPERATION,
                    field="operation_id",
                    message=message,
                )
            )
            continue
        operations.append(operation)
        operation_ids.add(operation.operation_id)
        exposure_ids.add(operation.exposure_id)

    for mitigator in portfolio.mitigators:
        if _row_already_seen(mitigator.row_id, seen_row_ids, issues):
            continue
        mitigators.append(mitigator)

    linked: list[Mitigator] = []
    for mitigator in mitigators:
        if mitigator.linked_operation_id not in operation_ids:
            issues.append(
                ValidationIssue(
                    code=IssueCode.ORPHAN_GUARANTEE,
                    field="granted_operation",
                    message="granted_operation does not match an operation",
                )
            )
            continue
        linked.append(mitigator)

    for operation in operations:
        has_linked_mitigator = any(
            mitigator.linked_operation_id == operation.operation_id for mitigator in linked
        )
        if operation.has_guarantee != has_linked_mitigator:
            issues.append(
                ValidationIssue(
                    code=IssueCode.FLAG_RELATION_MISMATCH,
                    field="has_guarantee",
                    message="has_guarantee does not match the linked guarantee rows",
                )
            )

    return CanonicalPortfolio(
        operations=operations,
        exposures=[
            Exposure(
                exposure_id=operation.exposure_id,
                operation_id=operation.operation_id,
                source_row_id=operation.row_id,
            )
            for operation in operations
        ],
        mitigators=linked,
        issues=issues,
    )


def _row_already_seen(row_id: str, seen_row_ids: set[str], issues: list[ValidationIssue]) -> bool:
    if row_id in seen_row_ids:
        issues.append(
            ValidationIssue(
                code=IssueCode.INVALID_SCHEMA,
                field="row_id",
                message="duplicate row_id",
            )
        )
        return True
    seen_row_ids.add(row_id)
    return False
