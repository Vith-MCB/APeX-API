"""Separação de operações e garantias do layout combined_v1."""

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
from pydantic import TypeAdapter, ValidationError

from app.core.enums import IssueCode
from app.core.money import parse_decimal
from app.domain.models.exposure import Operation
from app.domain.models.mitigator import Mitigator
from app.ingestion.parquet_reader import iter_batches
from app.ingestion.schemas import CombinedRecord, get_arrow_schema
from app.schemas.common import ValidationIssue

_MONEY_FIELDS = frozenset(
    {
        "balance_amount",
        "provided_exposure_amount",
        "guarantee_face_value",
        "collateral_market_value",
        "allocated_coverage_amount",
        "provided_fpr",
    }
)
_GUARANTEE_ZERO_FIELDS = frozenset(
    {
        "balance_amount",
        "provided_exposure_amount",
        "provided_fpr",
    }
)
_record_adapter = TypeAdapter(CombinedRecord)


@dataclass
class NormalizedPortfolio:
    operations: list[Operation] = field(default_factory=list)
    mitigators: list[Mitigator] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def split_records(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    operations: list[dict] = []
    guarantees: list[dict] = []
    for row in rows:
        if row.get("record_type") == "GUARANTEE":
            guarantees.append(row)
        elif row.get("record_type") == "OPERATION":
            operations.append(row)
    return operations, guarantees


def normalize_combined(
    path: Path,
    *,
    batch_size: int = 65_536,
    on_batch: Callable[[pa.RecordBatch], None] | None = None,
) -> NormalizedPortfolio:
    portfolio = NormalizedPortfolio()
    for batch in iter_batches(path, batch_size=batch_size):
        if on_batch is not None:
            on_batch(batch)
        _consume_batch(batch, portfolio)
    return portfolio


def _consume_batch(batch: pa.RecordBatch, portfolio: NormalizedPortfolio) -> None:
    allowed = set(get_arrow_schema("combined_v1").names)
    for row in batch.to_pylist():
        payload = {key: value for key, value in row.items() if key in allowed}
        record_type = payload.get("record_type")
        if record_type == "GUARANTEE":
            for key in _GUARANTEE_ZERO_FIELDS:
                if isinstance(payload.get(key), Decimal) and payload[key] == 0:
                    payload[key] = None
        converted = {key: _stringify_decimal(value) for key, value in payload.items()}
        try:
            record = _record_adapter.validate_python(converted)
        except ValidationError as exc:
            portfolio.issues.append(_issue_from_validation(converted, exc))
            continue
        if record.record_type == "OPERATION":
            portfolio.operations.append(_operation_from_record(record))
        else:
            portfolio.mitigators.append(_mitigator_from_record(record))


def _stringify_decimal(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    return value


def _issue_from_validation(payload: dict, exc: ValidationError) -> ValidationIssue:
    error = exc.errors()[0]
    location = error.get("loc", ())
    field_name = ".".join(str(part) for part in location) or "row"
    row_id = payload.get("row_id")
    prefix = row_id if isinstance(row_id, str) and row_id else "row"
    code = (
        IssueCode.INVALID_AMOUNT
        if any(part in _MONEY_FIELDS for part in location)
        else IssueCode.INVALID_SCHEMA
    )
    return ValidationIssue(
        code=code,
        field=f"{prefix}.{field_name}",
        message="row does not match the combined_v1 contract",
    )


def _operation_from_record(record) -> Operation:
    return Operation(
        row_id=record.row_id,
        operation_id=record.operation_id,
        exposure_id=record.exposure_id,
        reference_date=record.reference_date,
        product_type=record.product_type,
        balance_amount=parse_decimal(record.balance_amount),
        currency=record.currency,
        has_guarantee=record.has_guarantee,
        is_off_balance=record.is_off_balance,
    )


def _mitigator_from_record(record) -> Mitigator:
    face_value = record.guarantee_face_value
    return Mitigator(
        row_id=record.row_id,
        mitigator_id=record.mitigator_id,
        linked_operation_id=record.granted_operation,
        guarantee_type=record.guarantee_type,
        guarantee_face_value=None if face_value is None else parse_decimal(face_value),
    )


def operation_balance_total(operations: list[Operation]) -> Decimal:
    return sum((operation.balance_amount for operation in operations), Decimal("0.00"))
