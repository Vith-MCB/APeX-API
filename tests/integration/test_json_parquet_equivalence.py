"""O JSON didático e a linha exportada descrevem o mesmo recorte."""

from decimal import Decimal
from pathlib import Path

import duckdb
from fastapi.testclient import TestClient

from app.core.security import hash_file
from app.main import app
from app.reporting.exporter import write_results, write_traces, write_tranches
from app.reporting.portfolio import aggregate_portfolio, exports_from_calculation
from app.schemas.calculations import ExposureCalculationReport
from tests.unit.test_capital import _request

client = TestClient(app)


def test_didactic_json_matches_exported_subset_and_excludes_the_pending_row(tmp_path: Path) -> None:
    positive = client.post(
        "/api/v1/calculations/exposure",
        json=_request(scope="ARTICLE_1_INCLUDED"),
    )
    assert positive.status_code == 200
    positive_body = positive.json()

    pending_payload = _request(scope="ARTICLE_1_INCLUDED", subtype="GOLD")
    pending_payload["operation"]["operation_id"] = "OP-OPEN"
    pending_payload["operation"]["exposure_id"] = "EXP-OPEN"
    pending_payload["operation"]["balance_amount"] = "50.00"
    pending_payload["mitigators"][0]["linked_operation_id"] = "OP-OPEN"
    pending_payload["mitigators"][0]["mitigator_id"] = "MIT-OPEN"
    pending = client.post("/api/v1/calculations/exposure", json=pending_payload)
    assert pending.status_code == 200

    first_row, first_tranches, first_traces = exports_from_calculation(
        ExposureCalculationReport.model_validate(positive_body),
        job_id="didactic",
        row_source_id="row-art36",
        rule_set_version="0.3.0",
        input_sha256="canonical",
        balance_amount=Decimal("100000.00"),
        currency="BRL",
    )
    second_row, second_tranches, second_traces = exports_from_calculation(
        ExposureCalculationReport.model_validate(pending.json()),
        job_id="didactic",
        row_source_id="row-open",
        rule_set_version="0.3.0",
        input_sha256="canonical",
        balance_amount=Decimal("50.00"),
        currency="BRL",
    )
    rows = [first_row, second_row]
    tranches = [*first_tranches, *second_tranches]
    traces = [*first_traces, *second_traces]

    summary = aggregate_portfolio(
        rows,
        operation_row_count=2,
        guarantee_row_count=2,
        issue_count=0,
        balance_total=Decimal("100050.00"),
    )
    assert summary["calculated_subset_rwa"] == "38250.00"
    assert summary["calculated_subset_pr_contribution"] == "3060.00"
    assert summary["pending_balance"] == "50.00"
    assert summary["pending_exposure_count"] == 1

    first = tmp_path / "first"
    second = tmp_path / "second"
    _publish(first, rows, tranches, traces)
    _publish(second, rows, tranches, traces)
    for name in ("results.parquet", "tranches.parquet", "trace.parquet"):
        assert hash_file(first / name) == hash_file(second / name)

    connection = duckdb.connect()
    subset_rwa, kind = connection.execute(
        """
        SELECT SUM(rwa_after_mitigation), typeof(SUM(rwa_after_mitigation))
        FROM read_parquet(?)
        WHERE rwa_after_mitigation IS NOT NULL
        """,
        [str(first / "results.parquet")],
    ).fetchone()
    assert kind.startswith("DECIMAL")
    assert subset_rwa == Decimal("38250.00")

    exported = connection.execute(
        """
        SELECT exposure_amount_e, rwa_after_mitigation, minimum_pr_contribution
        FROM read_parquet(?)
        WHERE exposure_id = 'EXP-ART36'
        """,
        [str(first / "results.parquet")],
    ).fetchone()
    assert exported[0] == Decimal(positive_body["exposure_amount"])
    assert exported[1] == Decimal(positive_body["rwa_after_mitigation"])
    assert exported[2] == Decimal(positive_body["minimum_pr_contribution"])

    tranche_rows = connection.execute(
        """
        SELECT covered_amount, applied_fpr
        FROM read_parquet(?)
        ORDER BY tranche_id
        """,
        [str(first / "tranches.parquet")],
    ).fetchall()
    assert tranche_rows == [
        (Decimal("80000.00"), Decimal("0.0000000000")),
        (Decimal("45000.00"), Decimal("0.8500000000")),
    ]
    assert connection.execute(
        "SELECT COUNT(*) FROM read_parquet(?) WHERE exposure_id = 'EXP-OPEN'",
        [str(first / "tranches.parquet")],
    ).fetchone() == (0,)


def test_blocked_mode_export_has_no_prudential_numbers(tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/calculations/exposure",
        json=_request(mode="REGULATORY", scope="ARTICLE_1_INCLUDED"),
    )
    assert response.status_code == 200
    row, tranches, traces = exports_from_calculation(
        ExposureCalculationReport.model_validate(response.json()),
        job_id="regulatory",
        row_source_id="row-art36",
        rule_set_version="0.3.0",
        input_sha256="canonical",
        balance_amount=Decimal("100000.00"),
        currency="BRL",
    )
    assert row.exposure_amount_e is None
    assert row.rwa_before_mitigation is None
    assert row.rwa_after_mitigation is None
    assert row.minimum_pr_contribution is None
    assert tranches == []
    assert traces == []
    summary = aggregate_portfolio(
        [row],
        operation_row_count=1,
        guarantee_row_count=1,
        issue_count=0,
        balance_total=Decimal("100000.00"),
    )
    assert summary["calculated_subset_rwa"] is None


def _publish(directory: Path, rows, tranches, traces) -> None:
    directory.mkdir()
    write_results(directory / "results.parquet", rows)
    write_tranches(directory / "tranches.parquet", tranches)
    write_traces(directory / "trace.parquet", traces)
