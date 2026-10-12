"""Vínculos de garantias sem reconhecer mitigação prudencial."""

from decimal import Decimal

from app.ingestion.combined_normalizer import normalize_combined, operation_balance_total
from app.ingestion.fixture_loader import write_combined_parquet
from app.ingestion.relationship_validator import validate_links


def _operation(**overrides):
    row = {
        "record_type": "OPERATION",
        "row_id": "r1",
        "operation_id": "00012345",
        "exposure_id": "EXP-12345",
        "reference_date": "2026-09-30",
        "product_type": "SYNTHETIC_CREDIT",
        "balance_amount": "100.00",
        "currency": "BRL",
        "has_guarantee": False,
        "is_off_balance": False,
    }
    row.update(overrides)
    return row


def _guarantee(**overrides):
    row = {
        "record_type": "GUARANTEE",
        "row_id": "r2",
        "granted_operation": "00012345",
        "mitigator_id": "G-01",
        "guarantee_type": "FINANCIAL_COLLATERAL",
        "guarantee_face_value": "10.00",
    }
    row.update(overrides)
    return row


def _canonical(tmp_path, rows):
    destination = tmp_path / "links.parquet"
    write_combined_parquet(rows, destination)
    return validate_links(normalize_combined(destination))


def test_orphan_guarantee_is_not_linked(tmp_path):
    canonical = _canonical(
        tmp_path,
        [_operation(has_guarantee=False), _guarantee(granted_operation="MISSING")],
    )

    assert canonical.mitigators == []
    assert {issue.code for issue in canonical.issues} == {"ORPHAN_GUARANTEE"}


def test_duplicate_operation_with_a_different_balance_is_not_summed(tmp_path):
    canonical = _canonical(
        tmp_path,
        [
            _operation(),
            _operation(row_id="r9", balance_amount="250.00", exposure_id="EXP-999"),
        ],
    )

    assert len(canonical.operations) == 1
    assert operation_balance_total(canonical.operations) == Decimal("100.00")
    assert canonical.issues[0].code == "DUPLICATE_OPERATION"
    assert "different balance" in canonical.issues[0].message


def test_guarantee_flag_must_match_linked_rows(tmp_path):
    canonical = _canonical(tmp_path, [_operation(has_guarantee=False), _guarantee()])

    assert canonical.issues[0].code == "FLAG_RELATION_MISMATCH"
    assert len(canonical.mitigators) == 1


def test_duplicate_row_id_is_rejected(tmp_path):
    canonical = _canonical(
        tmp_path,
        [_operation(has_guarantee=True), _guarantee(row_id="r1")],
    )

    assert canonical.mitigators == []
    assert canonical.issues[0].code == "INVALID_SCHEMA"
    assert canonical.issues[0].field == "row_id"
