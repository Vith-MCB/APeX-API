"""Validação estrutural compartilhada dos vínculos de uma exposição."""

from app.core.enums import IssueCode
from app.schemas.common import ValidationIssue


def validate_exposure_links(
    *,
    operation_id: str,
    has_guarantee: bool,
    linked_operation_ids: tuple[str, ...],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    if has_guarantee != bool(linked_operation_ids):
        issues.append(
            ValidationIssue(
                code=IssueCode.FLAG_RELATION_MISMATCH,
                field="operation.has_guarantee",
                message="has_guarantee is inconsistent with the submitted mitigators",
            )
        )
    for index, linked_operation_id in enumerate(linked_operation_ids):
        if linked_operation_id != operation_id:
            issues.append(
                ValidationIssue(
                    code=IssueCode.ORPHAN_GUARANTEE,
                    field=f"mitigators.{index}.linked_operation_id",
                    message="linked_operation_id does not match operation.operation_id",
                )
            )
    return tuple(issues)
