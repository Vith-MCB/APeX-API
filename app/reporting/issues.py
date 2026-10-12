"""Issues de validação, sem a linha original."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from app.schemas.common import ValidationIssue


def export_issues(path: Path, issues: list[ValidationIssue]) -> None:
    table = pa.table(
        {
            "code": pa.array([issue.code for issue in issues], type=pa.string()),
            "field": pa.array([issue.field for issue in issues], type=pa.string()),
            "message": pa.array([issue.message for issue in issues], type=pa.string()),
        }
    )
    pq.write_table(table, path)
