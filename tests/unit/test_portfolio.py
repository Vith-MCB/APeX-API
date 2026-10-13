"""Subconjunto calculado, com pendências fora da soma."""

from datetime import date
from decimal import Decimal

from app.reporting.portfolio import ExposureExport, aggregate_portfolio


def test_subset_keeps_resolved_rows_and_excludes_pending_rwa() -> None:
    calculated = _row("EXP-1", "CALCULATED", after=Decimal("38250.00"), contribution=Decimal("3060.00"))
    pending = _row("EXP-2", "UNSUPPORTED", after=None, before=Decimal("106250.00"), balance=Decimal("50.00"))
    unchanged = _row(
        "EXP-3",
        "NOT_APPLICABLE",
        before=Decimal("106250.00"),
        after=Decimal("106250.00"),
        contribution=Decimal("8500.00"),
        balance=Decimal("10.00"),
    )

    summary = aggregate_portfolio(
        [calculated, pending, unchanged],
        operation_row_count=3,
        guarantee_row_count=2,
        issue_count=0,
        balance_total=Decimal("160.00"),
    )

    assert summary["calculated_subset_rwa"] == "144500.00"
    assert summary["calculated_subset_pr_contribution"] == "11560.00"
    assert summary["pending_exposure_count"] == 1
    assert summary["pending_balance"] == "50.00"
    assert summary["calculated_exposure_count"] == 2
    assert summary["coverage_ratio"] == "0.6667"
    assert "total_rwa_cpad" not in summary


def test_empty_subset_stays_null_and_zero_reduction_is_kept() -> None:
    row = _row(
        "EXP-0",
        "CALCULATED",
        before=Decimal("106250.00"),
        after=Decimal("106250.00"),
        contribution=Decimal("8500.00"),
    )
    assert row.rwa_reduction_amount == Decimal("0.00")
    assert row.rwa_reduction_ratio == Decimal("0.0000000000")

    summary = aggregate_portfolio(
        [_row("EXP-OPEN", "INSUFFICIENT_DATA", after=None)],
        operation_row_count=1,
        guarantee_row_count=0,
        issue_count=1,
        balance_total=Decimal("1.00"),
    )
    assert summary["calculated_subset_rwa"] is None
    assert summary["calculated_subset_pr_contribution"] is None
    assert summary["coverage_ratio"] == "0.0000"


def test_reduction_keeps_the_sign_of_the_difference() -> None:
    increased = _row(
        "EXP-UP",
        "CALCULATED",
        before=Decimal("10.00"),
        after=Decimal("12.00"),
    )
    assert increased.rwa_reduction_amount == Decimal("-2.00")
    assert increased.rwa_reduction_ratio < 0


def _row(
    exposure_id: str,
    status: str,
    *,
    before: Decimal | None = Decimal("106250.00"),
    after: Decimal | None = None,
    contribution: Decimal | None = None,
    balance: Decimal = Decimal("100.00"),
) -> ExposureExport:
    amount, ratio = (None, None)
    if before is not None and after is not None:
        amount = before - after
        ratio = (amount / before).quantize(Decimal("0.0000000001"))
    return ExposureExport(
        job_id="job",
        row_source_id=exposure_id,
        operation_id=exposure_id,
        exposure_id=exposure_id,
        reference_date=date(2026, 9, 30),
        calculation_mode="DIDACTIC",
        status=status,
        rule_set_version="0.3.0",
        exposure_amount_e=Decimal("125000.00") if before is not None else None,
        fpr_original=Decimal("0.85") if before is not None else None,
        rwa_before_mitigation=before,
        rwa_after_mitigation=after,
        rwa_delta=amount,
        rwa_reduction_amount=amount,
        rwa_reduction_ratio=ratio,
        minimum_pr_contribution=contribution,
        currency="BRL",
        mitigator_count=1,
        tranche_count=0,
        issue_codes="",
        trace_ref=exposure_id if after is not None else None,
        input_sha256="abc",
        balance_amount=balance,
    )
