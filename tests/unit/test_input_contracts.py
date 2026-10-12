"""Contratos estruturais dos registros e do schema Arrow."""

import json
from pathlib import Path

import pyarrow as pa
import pytest
from pydantic import TypeAdapter, ValidationError

from app.ingestion.schemas import CombinedRecord, get_arrow_schema
from app.schemas.operations import OperationInput

REPOSITORY_ROOT = Path(__file__).parents[2]
combined_record_adapter = TypeAdapter(CombinedRecord)


def test_operation_id_preserves_leading_zeroes():
    operation = OperationInput(
        operation_id="00012345",
        exposure_id="EXP-12345",
        product_type="SYNTHETIC_CREDIT",
        balance_amount="100000.00",
        currency="BRL",
        has_guarantee=False,
        is_off_balance=False,
    )

    assert operation.operation_id == "00012345"


def test_numeric_operation_id_is_rejected():
    with pytest.raises(ValidationError):
        OperationInput(
            operation_id=12345,
            exposure_id="EXP-12345",
            product_type="SYNTHETIC_CREDIT",
            balance_amount="100000.00",
            currency="BRL",
            has_guarantee=False,
            is_off_balance=False,
        )


def test_combined_example_parses_by_record_type():
    records = [
        combined_record_adapter.validate_python(json.loads(line))
        for line in (REPOSITORY_ROOT / "examples/combined_input.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]

    assert [record.record_type for record in records] == [
        "OPERATION",
        "GUARANTEE",
        "GUARANTEE",
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("balance_amount", 100000.00),
        ("balance_amount", "NaN"),
    ],
)
def test_invalid_balance_amount_points_to_the_field(field, value):
    payload = {
        "operation_id": "00012345",
        "exposure_id": "EXP-12345",
        "product_type": "SYNTHETIC_CREDIT",
        "balance_amount": "100000.00",
        "currency": "BRL",
        "has_guarantee": False,
        "is_off_balance": False,
    }
    payload[field] = value

    with pytest.raises(ValidationError) as error:
        OperationInput.model_validate(payload)

    assert error.value.errors()[0]["loc"] == ("balance_amount",)


def test_missing_balance_amount_points_to_the_field():
    payload = {
        "operation_id": "00012345",
        "exposure_id": "EXP-12345",
        "product_type": "SYNTHETIC_CREDIT",
        "currency": "BRL",
        "has_guarantee": False,
        "is_off_balance": False,
    }

    with pytest.raises(ValidationError) as error:
        OperationInput.model_validate(payload)

    assert error.value.errors()[0]["loc"] == ("balance_amount",)


def test_combined_arrow_schema_preserves_identifiers_and_decimal_money():
    schema = get_arrow_schema("combined_v1")

    assert schema.field("operation_id").type == pa.string()
    assert pa.types.is_decimal(schema.field("balance_amount").type)
    assert not any(field.name.startswith("rwa_") for field in schema)


def test_unknown_arrow_schema_version_is_rejected():
    with pytest.raises(ValueError, match="unsupported schema version"):
        get_arrow_schema("combined_v2")
