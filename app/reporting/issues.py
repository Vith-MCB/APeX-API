"""Exporta issues estruturais sem perder code, field e message."""

from pathlib import Path

from app.reporting.exporter import write_issues
from app.reporting.portfolio import IssueExport
from app.schemas.common import ValidationIssue


def export_issues(path: Path, issues: list[ValidationIssue]) -> None:
    write_issues(
        path,
        [
            IssueExport(
                code=issue.code,
                field=issue.field,
                message=issue.message,
                operation_id=None,
                exposure_id=None,
                mitigator_id=None,
                status="STRUCTURAL",
            )
            for issue in issues
        ],
    )
