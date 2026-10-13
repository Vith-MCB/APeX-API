"""FPR original do art. 36, sem usar saldo e sem liberar o modo regulatório."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.enums import (
    CalculationMode,
    CalculationStatus,
    CounterpartyLegalNature,
    ExposureValueBasis,
    PrudentialCategoryConflictStatus,
)
from app.domain.rules.bcb229 import ORIGINAL_FPR, Art36Input
from app.domain.services.fpr import resolve_original_fpr
from app.main import app

REFERENCE_DATE = date(2026, 9, 30)
DECLARED_EXPOSURE = Decimal("125000.00")
ACCOUNTING_BALANCE = Decimal("100000.00")


def test_didactic_uses_declared_exposure_and_article_36_fpr() -> None:
    decision = resolve_original_fpr(_complete_input(), CalculationMode.DIDACTIC)

    assert decision.status is CalculationStatus.CALCULATED
    assert decision.exposure_amount == DECLARED_EXPOSURE
    assert decision.exposure_amount != ACCOUNTING_BALANCE
    assert decision.original_fpr == ORIGINAL_FPR
    assert decision.didactic_not_regulatory is True
    assert decision.regulatory_calculation is False


def test_balance_without_declared_exposure_has_no_number() -> None:
    decision = resolve_original_fpr(
        _complete_input(provided_exposure_amount=None, exposure_value_basis=None),
        CalculationMode.DIDACTIC,
    )

    assert decision.status is CalculationStatus.INSUFFICIENT_DATA
    assert decision.exposure_amount is None
    assert decision.original_fpr is None
    assert "missing_declared_exposure_amount" in decision.reasons


def test_missing_total_assets_has_no_fpr() -> None:
    decision = resolve_original_fpr(
        _complete_input(total_assets=None),
        CalculationMode.DIDACTIC,
    )

    assert decision.status is CalculationStatus.INSUFFICIENT_DATA
    assert "missing_total_assets" in decision.reasons
    assert decision.original_fpr is None


def test_revenue_at_upper_limit_is_not_applicable() -> None:
    decision = resolve_original_fpr(
        _complete_input(annual_gross_revenue=Decimal("300000000.00")),
        CalculationMode.DIDACTIC,
    )

    assert decision.status is CalculationStatus.NOT_APPLICABLE
    assert decision.original_fpr is None


def test_asset_limit_is_not_applicable() -> None:
    decision = resolve_original_fpr(
        _complete_input(total_assets=Decimal("240000000.00")),
        CalculationMode.DIDACTIC,
    )

    assert decision.status is CalculationStatus.NOT_APPLICABLE
    assert decision.original_fpr is None


def test_revenue_below_retail_threshold_is_unsupported() -> None:
    decision = resolve_original_fpr(
        _complete_input(annual_gross_revenue=Decimal("14999999.99")),
        CalculationMode.DIDACTIC,
    )

    assert decision.status is CalculationStatus.UNSUPPORTED
    assert decision.original_fpr is None


def test_reference_date_before_cut_is_unsupported() -> None:
    decision = resolve_original_fpr(
        _complete_input(reference_date=date(2023, 6, 30)),
        CalculationMode.DIDACTIC,
    )

    assert decision.status is CalculationStatus.UNSUPPORTED
    assert decision.original_fpr is None


def test_off_balance_exposure_is_unsupported() -> None:
    decision = resolve_original_fpr(
        _complete_input(is_off_balance=True),
        CalculationMode.DIDACTIC,
    )

    assert decision.status is CalculationStatus.UNSUPPORTED
    assert decision.original_fpr is None


def test_negative_declared_exposure_is_invalid() -> None:
    decision = resolve_original_fpr(
        _complete_input(provided_exposure_amount=Decimal("-1.00")),
        CalculationMode.DIDACTIC,
    )

    assert decision.status is CalculationStatus.INVALID_INPUT
    assert decision.original_fpr is None


def test_divergent_provided_fpr_is_ignored() -> None:
    decision = resolve_original_fpr(
        _complete_input(provided_fpr=Decimal("0.90")),
        CalculationMode.DIDACTIC,
    )

    assert decision.original_fpr == ORIGINAL_FPR
    assert decision.issues[0].code == "PROVIDED_FPR_IGNORED"


def test_regulatory_mode_hides_the_candidate_number() -> None:
    decision = resolve_original_fpr(_complete_input(), CalculationMode.REGULATORY)

    assert decision.status is CalculationStatus.REQUIRES_REVIEW
    assert decision.exposure_amount is None
    assert decision.original_fpr is None
    assert "regulatory_blocked_while_in_review" in decision.reasons
    assert decision.regulatory_calculation is False


def test_calculation_endpoint_publishes_didactic_result_only() -> None:
    client = TestClient(app)
    didactic = client.post("/api/v1/calculations/exposure", json=_request("DIDACTIC"))
    regulatory = client.post("/api/v1/calculations/exposure", json=_request("REGULATORY"))

    assert didactic.status_code == 200
    didactic_body = didactic.json()
    assert didactic_body["exposure_amount"] == "125000.00"
    assert didactic_body["original_fpr"] == "0.85"
    assert didactic_body["didactic_not_regulatory"] is True
    assert didactic_body["regulatory_calculation"] is False
    assert "rwa" not in didactic_body
    assert "capital_contribution" not in didactic_body

    assert regulatory.status_code == 200
    regulatory_body = regulatory.json()
    assert regulatory_body["calculation_status"] == "REQUIRES_REVIEW"
    assert regulatory_body["exposure_amount"] is None
    assert regulatory_body["original_fpr"] is None
    assert regulatory_body["regulatory_calculation"] is False


def _complete_input(**overrides: object) -> Art36Input:
    values: dict[str, object] = {
        "reference_date": REFERENCE_DATE,
        "is_off_balance": False,
        "counterparty_legal_nature": CounterpartyLegalNature.PRIVATE_LEGAL_ENTITY,
        "counterparty_is_financial": False,
        "total_assets": Decimal("100000000.00"),
        "annual_gross_revenue": Decimal("15000000.00"),
        "financial_year_end": date(2025, 12, 31),
        "financial_data_is_latest_available": True,
        "prudential_category_conflict_status": PrudentialCategoryConflictStatus.NONE_DECLARED,
        "balance_amount": ACCOUNTING_BALANCE,
        "provided_exposure_amount": DECLARED_EXPOSURE,
        "exposure_value_basis": ExposureValueBasis.INSTITUTION_DECLARED_ART5_ART6,
        "provided_fpr": None,
    }
    values.update(overrides)
    return Art36Input(**values)  # type: ignore[arg-type]


def _request(mode: str) -> dict[str, object]:
    return {
        "context": {
            "schema_version": "combined_v1",
            "reference_date": "2026-09-30",
            "institution_profile": "UNDEFINED",
            "capital_regime": "UNDEFINED",
            "collateral_approach": "SIMPLE",
            "rule_set_version": "0.3.0",
            "calculation_mode": mode,
            "reporting_currency": "BRL",
            "strict_mode": True,
        },
        "operation": {
            "operation_id": "OP-ART36",
            "exposure_id": "EXP-ART36",
            "product_type": "SYNTHETIC",
            "balance_amount": "100000.00",
            "currency": "BRL",
            "has_guarantee": False,
            "is_off_balance": False,
            "counterparty_legal_nature": "PRIVATE_LEGAL_ENTITY",
            "counterparty_is_financial": False,
            "counterparty_total_assets": "100000000.00",
            "counterparty_annual_gross_revenue": "15000000.00",
            "counterparty_financial_year_end": "2025-12-31",
            "financial_data_is_latest_available": True,
            "prudential_category_conflict_status": "NONE_DECLARED",
            "provided_exposure_amount": "125000.00",
            "exposure_value_basis": "INSTITUTION_DECLARED_ART5_ART6",
        },
        "mitigators": [],
    }
