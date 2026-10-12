"""Separação de combined_v1 e preservação de zero legítimo."""

from decimal import Decimal
from pathlib import Path

from app.ingestion.combined_normalizer import (
    normalize_combined,
    operation_balance_total,
    split_records,
)
from app.ingestion.fixture_loader import jsonl_to_parquet, write_combined_parquet
from app.ingestion.relationship_validator import validate_links

ROOT = Path(__file__).parents[2]


def test_split_records_keeps_guarantees_out_of_operations():
    operations, guarantees = split_records(
        [
            {"record_type": "OPERATION", "row_id": "r1"},
            {"record_type": "GUARANTEE", "row_id": "r2"},
            {"record_type": "GUARANTEE", "row_id": "r3"},
        ]
    )

    assert [row["row_id"] for row in operations] == ["r1"]
    assert [row["row_id"] for row in guarantees] == ["r2", "r3"]


def test_example_file_keeps_the_operation_balance(tmp_path):
    destination = tmp_path / "combined.parquet"
    jsonl_to_parquet(ROOT / "examples/combined_input.jsonl", destination)

    canonical = validate_links(normalize_combined(destination, batch_size=1))

    assert len(canonical.operations) == 1
    assert len(canonical.exposures) == 1
    assert len(canonical.mitigators) == 2
    assert canonical.exposures[0].exposure_id == "EXP-12345"
    assert operation_balance_total(canonical.operations) == Decimal("100000.00")
    assert canonical.issues == []


def test_legacy_zero_on_a_guarantee_does_not_erase_real_zeroes(tmp_path):
    destination = tmp_path / "zeros.parquet"
    write_combined_parquet(
        [
            {
                "record_type": "OPERATION",
                "row_id": "r1",
                "operation_id": "00012345",
                "exposure_id": "EXP-12345",
                "reference_date": "2026-09-30",
                "product_type": "SYNTHETIC_CREDIT",
                "balance_amount": "0.00",
                "currency": "BRL",
                "has_guarantee": True,
                "is_off_balance": False,
            },
            {
                "record_type": "GUARANTEE",
                "row_id": "r2",
                "granted_operation": "00012345",
                "mitigator_id": "G-01",
                "guarantee_type": "FINANCIAL_COLLATERAL",
                "balance_amount": "0.00",
                "guarantee_face_value": "0.00",
                "provided_fpr": "0.00",
            },
        ],
        destination,
    )

    canonical = validate_links(normalize_combined(destination))

    assert canonical.issues == []
    assert canonical.operations[0].balance_amount == Decimal("0")
    assert canonical.mitigators[0].guarantee_face_value == Decimal("0")
    assert operation_balance_total(canonical.operations) == Decimal("0")
