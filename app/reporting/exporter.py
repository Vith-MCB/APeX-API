"""Grava Parquet e JSON do lote com esquema estável."""

import json
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from app.core.money import quantize_money
from app.core.security import hash_file
from app.reporting.portfolio import ExposureExport, IssueExport, TraceExport, TrancheExport

_MONEY = pa.decimal128(38, 2)
_FACTOR = pa.decimal128(38, 10)
_FACTOR_SCALE = Decimal("0.0000000001")


def write_results(path: Path, rows: list[ExposureExport]) -> None:
    ordered = sorted(rows, key=lambda row: (row.exposure_id, row.row_source_id))
    table = pa.table(
        {
            "job_id": pa.array([row.job_id for row in ordered], type=pa.string()),
            "row_source_id": pa.array([row.row_source_id for row in ordered], type=pa.string()),
            "operation_id": pa.array([row.operation_id for row in ordered], type=pa.string()),
            "exposure_id": pa.array([row.exposure_id for row in ordered], type=pa.string()),
            "reference_date": pa.array(
                [row.reference_date for row in ordered], type=pa.date32()
            ),
            "calculation_mode": pa.array(
                [row.calculation_mode for row in ordered], type=pa.string()
            ),
            "status": pa.array([row.status for row in ordered], type=pa.string()),
            "rule_set_version": pa.array(
                [row.rule_set_version for row in ordered], type=pa.string()
            ),
            "exposure_amount_e": _money_array([row.exposure_amount_e for row in ordered]),
            "fpr_original": _factor_array([row.fpr_original for row in ordered]),
            "rwa_before_mitigation": _money_array([row.rwa_before_mitigation for row in ordered]),
            "rwa_after_mitigation": _money_array([row.rwa_after_mitigation for row in ordered]),
            "rwa_delta": _money_array([row.rwa_delta for row in ordered]),
            "rwa_reduction_amount": _money_array([row.rwa_reduction_amount for row in ordered]),
            "rwa_reduction_ratio": _factor_array([row.rwa_reduction_ratio for row in ordered]),
            "minimum_pr_contribution": _money_array(
                [row.minimum_pr_contribution for row in ordered]
            ),
            "currency": pa.array([row.currency for row in ordered], type=pa.string()),
            "mitigator_count": pa.array([row.mitigator_count for row in ordered], type=pa.int64()),
            "tranche_count": pa.array([row.tranche_count for row in ordered], type=pa.int64()),
            "issue_codes": pa.array([row.issue_codes for row in ordered], type=pa.string()),
            "trace_ref": pa.array([row.trace_ref for row in ordered], type=pa.string()),
            "input_sha256": pa.array([row.input_sha256 for row in ordered], type=pa.string()),
        }
    )
    _write_table(path, table)


def write_tranches(path: Path, rows: list[TrancheExport]) -> None:
    ordered = sorted(rows, key=lambda row: (row.exposure_id, row.tranche_id))
    table = pa.table(
        {
            "exposure_id": pa.array([row.exposure_id for row in ordered], type=pa.string()),
            "tranche_id": pa.array([row.tranche_id for row in ordered], type=pa.string()),
            "mitigator_id": pa.array([row.mitigator_id for row in ordered], type=pa.string()),
            "tranche_kind": pa.array([row.tranche_kind for row in ordered], type=pa.string()),
            "covered_amount": _money_array([row.covered_amount for row in ordered]),
            "applied_fpr": _factor_array([row.applied_fpr for row in ordered]),
            "tranche_rwa": _money_array([row.tranche_rwa for row in ordered]),
            "treatment_id": pa.array([row.treatment_id for row in ordered], type=pa.string()),
            "rule_id": pa.array([row.rule_id for row in ordered], type=pa.string()),
            "rounding_stage": pa.array([row.rounding_stage for row in ordered], type=pa.string()),
            "eligibility_status": pa.array(
                [row.eligibility_status for row in ordered], type=pa.string()
            ),
            "source_row_id": pa.array([row.source_row_id for row in ordered], type=pa.string()),
            "status": pa.array([row.status for row in ordered], type=pa.string()),
        }
    )
    _write_table(path, table)


def write_traces(path: Path, rows: list[TraceExport]) -> None:
    ordered = sorted(rows, key=lambda row: (row.exposure_id, row.rule_id, row.article))
    table = pa.table(
        {
            "exposure_id": pa.array([row.exposure_id for row in ordered], type=pa.string()),
            "rule_id": pa.array([row.rule_id for row in ordered], type=pa.string()),
            "article": pa.array([row.article for row in ordered], type=pa.string()),
            "factor": pa.array([row.factor for row in ordered], type=pa.string()),
        }
    )
    _write_table(path, table)


def write_issues(path: Path, rows: list[IssueExport]) -> None:
    ordered = sorted(rows, key=lambda row: (row.field, row.code, row.message))
    table = pa.table(
        {
            "code": pa.array([row.code for row in ordered], type=pa.string()),
            "field": pa.array([row.field for row in ordered], type=pa.string()),
            "message": pa.array([row.message for row in ordered], type=pa.string()),
            "operation_id": pa.array([row.operation_id for row in ordered], type=pa.string()),
            "exposure_id": pa.array([row.exposure_id for row in ordered], type=pa.string()),
            "mitigator_id": pa.array([row.mitigator_id for row in ordered], type=pa.string()),
            "status": pa.array([row.status for row in ordered], type=pa.string()),
        }
    )
    _write_table(path, table)


def write_summary(path: Path, summary: dict[str, object]) -> None:
    path.write_text(
        json.dumps(summary, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.write_text(
        json.dumps(manifest, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def artifact_hashes(directory: Path, names: list[str]) -> dict[str, str]:
    return {name: hash_file(directory / name) for name in names}


def _write_table(path: Path, table: pa.Table) -> None:
    pq.write_table(table, path, compression="NONE", write_statistics=False)


def _money_array(values: list[Decimal | None]) -> pa.Array:
    return pa.array(
        [None if value is None else quantize_money(value, 2) for value in values],
        type=_MONEY,
    )


def _factor_array(values: list[Decimal | None]) -> pa.Array:
    return pa.array(
        [
            None if value is None else value.quantize(_FACTOR_SCALE)
            for value in values
        ],
        type=_FACTOR,
    )
