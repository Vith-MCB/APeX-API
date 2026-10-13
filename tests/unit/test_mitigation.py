"""Parcelas de um título público federal. O modo regulatório continua sem número."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.enums import CalculationStatus
from app.main import app


def test_one_eligible_bond_splits_the_declared_exposure() -> None:
    response = TestClient(app).post("/api/v1/calculations/exposure", json=_request("DIDACTIC"))

    assert response.status_code == 200
    body = response.json()
    assert body["exposure_amount"] == "125000.00"
    assert body["original_fpr"] == "0.85"
    assert body["didactic_not_regulatory"] is True
    assert body["regulatory_calculation"] is False
    assert body["mitigation_status"] == "CALCULATED"
    covered, uncovered = body["tranches"]
    assert covered["amount"] == "80000.00"
    assert covered["fpr"] == "0"
    assert uncovered["amount"] == "45000.00"
    assert uncovered["fpr"] == "0.85"
    assert Decimal(covered["amount"]) + Decimal(uncovered["amount"]) == Decimal("125000.00")
    assert "rwa" not in body
    assert "capital_contribution" not in body


def test_regulatory_and_validation_modes_hide_tranches() -> None:
    client = TestClient(app)
    for mode in ("REGULATORY", "VALIDATION_ONLY"):
        body = client.post("/api/v1/calculations/exposure", json=_request(mode)).json()
        assert body["calculation_status"] == "REQUIRES_REVIEW"
        assert body["mitigation_status"] == "REQUIRES_REVIEW"
        assert body["exposure_amount"] is None
        assert body["original_fpr"] is None
        assert body["tranches"] == []
        assert body["regulatory_calculation"] is False


def test_ineligible_subtype_has_no_tranche() -> None:
    body = _post(_request("DIDACTIC", collateral_subtype="GOLD"))

    assert body["mitigation_status"] == CalculationStatus.UNSUPPORTED
    assert body["tranches"] == []
    assert "collateral_subtype_out_of_cut" in body["mitigation_reasons"]


def test_currency_mismatch_has_no_tranche() -> None:
    body = _post(_request("DIDACTIC", guarantee_currency="USD"))

    assert body["mitigation_status"] == CalculationStatus.UNSUPPORTED
    assert "currency_mismatch" in body["mitigation_reasons"]
    assert body["tranches"] == []


def test_shorter_collateral_maturity_is_not_applicable() -> None:
    body = _post(_request("DIDACTIC", collateral_effective_maturity_date="2026-12-31"))

    assert body["mitigation_status"] == CalculationStatus.NOT_APPLICABLE
    assert "collateral_matures_before_exposure" in body["mitigation_reasons"]
    assert body["tranches"] == []


def test_missing_market_value_has_no_number() -> None:
    payload = _request("DIDACTIC")
    payload["mitigators"][0].pop("collateral_market_value")
    body = _post(payload)

    assert body["mitigation_status"] == CalculationStatus.INSUFFICIENT_DATA
    assert "missing_market_value" in body["mitigation_reasons"]
    assert body["tranches"] == []


def test_overlap_requires_review_without_allocation() -> None:
    body = _post(_request("DIDACTIC", overlap_status="PRESENT"))

    assert body["mitigation_status"] == CalculationStatus.REQUIRES_REVIEW
    assert "collateral_overlap" in body["mitigation_reasons"]
    assert body["tranches"] == []


def test_two_guarantees_keep_their_links_and_do_not_split_exposure() -> None:
    payload = _request("DIDACTIC")
    second = dict(payload["mitigators"][0])
    second["mitigator_id"] = "MIT-2"
    payload["mitigators"].append(second)
    body = _post(payload)

    assert body["mitigator_ids"] == ["MIT-1", "MIT-2"]
    assert body["mitigation_status"] == CalculationStatus.UNSUPPORTED
    assert "multiple_mitigators_not_in_cut" in body["mitigation_reasons"]
    assert body["tranches"] == []
    assert body["exposure_amount"] == "125000.00"


def test_validation_endpoint_stays_structural() -> None:
    response = TestClient(app).post("/api/v1/validate/exposure", json=_request("VALIDATION_ONLY"))

    assert response.status_code == 200
    body = response.json()
    assert body["mitigator_count"] == 1
    assert body["regulatory_calculation"] is False
    assert "tranches" not in body
    assert "original_fpr" not in body
    assert "rwa" not in body


def _post(payload: dict[str, object]) -> dict[str, object]:
    response = TestClient(app).post("/api/v1/calculations/exposure", json=payload)
    assert response.status_code == 200
    return response.json()


def _request(mode: str, **collateral: object) -> dict[str, object]:
    mitigator = {
        "mitigator_id": "MIT-1",
        "linked_operation_id": "OP-ART36",
        "guarantee_type": "COLLATERAL",
        "collateral_subtype": "FEDERAL_PUBLIC_BOND",
        "collateral_market_value": "100000.00",
        "guarantee_currency": "BRL",
        "market_value_as_of": "2026-09-30",
        "mark_to_market_frequency": "DAILY",
        "collateral_effective_maturity_date": "2028-09-30",
        "overlap_status": "NONE",
        "association_scope": "UNIQUE_EXPOSURE",
        "institution_requirements_status": "DECLARED",
    }
    mitigator.update(collateral)
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
        "mitigators": [mitigator],
    }
