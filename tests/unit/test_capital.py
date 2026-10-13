"""RWA do recorte e contribuição isolada de PR."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.enums import TrancheType
from app.domain.models.tranche import ExposureTranche
from app.domain.services.rwa import calculate_rwa
from app.main import app

client = TestClient(app)


def test_didactic_calculates_rwa_and_minimum_pr_contribution() -> None:
    body = _calculate(_request(scope="ARTICLE_1_INCLUDED"))

    assert body["rwa_before_mitigation"] == "106250.00"
    assert body["rwa_after_mitigation"] == "38250.00"
    assert body["rwa_delta"] == "68000.00"
    assert body["minimum_pr_contribution"] == "3060.00"
    assert body["minimum_pr_status"] == "CALCULATED"
    assert body["complete_regulatory_coverage"] is False
    assert [item["rwa_contribution"] for item in body["tranches"]] == [
        "0.00",
        "38250.00",
    ]
    assert {item["rule_id"] for item in body["applied_rules"]} == {
        "BCB229_ART36_PJ_NAO_FINANCEIRA",
        "CIRC3809_SIMPLE_TPF_BRL",
        "CMN4958_MINIMUM_PR",
    }


def test_api_money_matches_the_decimal_domain_result() -> None:
    body = _calculate(_request(scope="ARTICLE_1_INCLUDED"))
    tranches = (
        ExposureTranche(
            TrancheType.COVERED_COLLATERAL_SIMPLE,
            Decimal("80000.00"),
            Decimal("0"),
            "CIRC3809_SIMPLE_TPF_BRL",
            "6",
        ),
        ExposureTranche(
            TrancheType.UNCOVERED,
            Decimal("45000.00"),
            Decimal("0.85"),
            "BCB229_ART36_PJ_NAO_FINANCEIRA",
            "36",
        ),
    )
    domain = calculate_rwa(Decimal("125000.00"), Decimal("0.85"), tranches)
    assert Decimal(body["rwa_before_mitigation"]) == domain.before_mitigation
    assert Decimal(body["rwa_after_mitigation"]) == domain.after_mitigation
    assert Decimal(body["rwa_delta"]) == domain.delta


def test_exposure_without_guarantee_keeps_baseline_rwa() -> None:
    payload = _request(scope="ARTICLE_1_INCLUDED")
    payload["operation"]["has_guarantee"] = False
    payload["mitigators"] = []
    body = _calculate(payload)

    assert body["rwa_before_mitigation"] == "106250.00"
    assert body["rwa_after_mitigation"] == "106250.00"
    assert body["rwa_delta"] == "0.00"
    assert body["minimum_pr_contribution"] == "8500.00"
    assert body["tranches"] == []


def test_ineligible_guarantee_does_not_reduce_rwa() -> None:
    body = _calculate(_request(scope="ARTICLE_1_INCLUDED", subtype="GOLD"))

    assert body["mitigation_status"] == "UNSUPPORTED"
    assert body["rwa_before_mitigation"] == "106250.00"
    assert body["rwa_after_mitigation"] == "106250.00"
    assert body["rwa_delta"] == "0.00"
    assert body["tranches"] == []


@pytest.mark.parametrize("scope", [None, "UNKNOWN"])
def test_missing_scope_keeps_rwa_and_omits_contribution(scope: str | None) -> None:
    body = _calculate(_request(scope=scope))

    assert body["rwa_after_mitigation"] == "38250.00"
    assert body["minimum_pr_contribution"] is None
    assert body["minimum_pr_status"] == "INSUFFICIENT_DATA"
    assert "missing_minimum_pr_scope" in body["minimum_pr_reasons"]


@pytest.mark.parametrize(
    ("scope", "status", "reason"),
    [
        ("ARTICLE_1_EXCLUDED", "NOT_APPLICABLE", "institution_excluded_by_article_1"),
        ("SEGMENT_5", "NOT_APPLICABLE", "segment_5_out_of_scope"),
        ("CREDIT_COOPERATIVE_ART7", "UNSUPPORTED", "article_7_addition_not_implemented"),
    ],
)
def test_out_of_scope_context_does_not_apply_eight_percent(
    scope: str,
    status: str,
    reason: str,
) -> None:
    body = _calculate(_request(scope=scope))

    assert body["rwa_after_mitigation"] == "38250.00"
    assert body["minimum_pr_contribution"] is None
    assert body["minimum_pr_status"] == status
    assert reason in body["minimum_pr_reasons"]
    assert "CMN4958_MINIMUM_PR" not in {
        item["rule_id"] for item in body["applied_rules"]
    }


@pytest.mark.parametrize("mode", ["REGULATORY", "VALIDATION_ONLY"])
def test_blocked_modes_publish_no_prudential_numbers(mode: str) -> None:
    body = _calculate(_request(mode=mode, scope="ARTICLE_1_INCLUDED"))

    assert body["exposure_amount"] is None
    assert body["original_fpr"] is None
    assert body["tranches"] == []
    assert body["rwa_before_mitigation"] is None
    assert body["rwa_after_mitigation"] is None
    assert body["rwa_delta"] is None
    assert body["minimum_pr_contribution"] is None
    assert body["minimum_pr_status"] is None
    assert body["applied_rules"] == []


def test_structural_validation_still_has_no_rwa_or_capital() -> None:
    response = client.post("/api/v1/validate/exposure", json=_request())

    assert response.status_code == 200
    body = response.json()
    assert "rwa_before_mitigation" not in body
    assert "rwa_after_mitigation" not in body
    assert "minimum_pr_contribution" not in body


def _calculate(payload: dict[str, object]) -> dict[str, object]:
    response = client.post("/api/v1/calculations/exposure", json=payload)
    assert response.status_code == 200
    return response.json()


def _request(
    *,
    mode: str = "DIDACTIC",
    scope: str | None = None,
    subtype: str = "FEDERAL_PUBLIC_BOND",
) -> dict[str, object]:
    context: dict[str, object] = {
        "schema_version": "combined_v1",
        "reference_date": "2026-09-30",
        "institution_profile": "SYNTHETIC_ART1_INSTITUTION",
        "capital_regime": "STANDARDIZED_CREDIT",
        "collateral_approach": "SIMPLE",
        "rule_set_version": "0.3.0",
        "calculation_mode": mode,
        "reporting_currency": "BRL",
        "strict_mode": True,
    }
    if scope is not None:
        context["minimum_pr_scope"] = scope
    return {
        "context": context,
        "operation": {
            "operation_id": "OP-ART36",
            "exposure_id": "EXP-ART36",
            "product_type": "SYNTHETIC",
            "balance_amount": "100000.00",
            "currency": "BRL",
            "has_guarantee": True,
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
            "exposure_effective_maturity_date": "2027-09-30",
        },
        "mitigators": [
            {
                "mitigator_id": "MIT-1",
                "linked_operation_id": "OP-ART36",
                "guarantee_type": "COLLATERAL",
                "collateral_subtype": subtype,
                "collateral_market_value": "100000.00",
                "guarantee_currency": "BRL",
                "market_value_as_of": "2026-09-30",
                "mark_to_market_frequency": "DAILY",
                "collateral_effective_maturity_date": "2028-09-30",
                "overlap_status": "NONE",
                "association_scope": "UNIQUE_EXPOSURE",
                "institution_requirements_status": "DECLARED",
            }
        ],
    }
