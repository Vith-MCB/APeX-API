"""Parcelas de um título público federal. O modo regulatório continua sem número."""

from decimal import Decimal

import pytest
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


@pytest.mark.parametrize(
    ("value", "expected_status", "reason"),
    [
        (True, "UNSUPPORTED", "article_7_otc_derivative_out_of_cut"),
        (None, "INSUFFICIENT_DATA", "missing_otc_derivative_declaration"),
    ],
)
def test_article_7_route_never_receives_covered_zero_fpr(
    value: bool | None,
    expected_status: str,
    reason: str,
) -> None:
    payload = _request("DIDACTIC")
    if value is None:
        payload["operation"].pop("is_otc_derivative")
    else:
        payload["operation"]["is_otc_derivative"] = value
    body = _post(payload)

    assert body["mitigation_status"] == expected_status
    assert reason in body["mitigation_reasons"]
    _assert_no_covered_zero_fpr(body)


@pytest.mark.parametrize(
    ("guarantee_type", "expected_status", "reason"),
    [
        ("FIDUCIARY_GUARANTEE", "UNSUPPORTED", "guarantee_type_out_of_cut"),
        (None, "INSUFFICIENT_DATA", "missing_guarantee_type"),
    ],
)
def test_guarantee_nature_must_be_financial_collateral(
    guarantee_type: str | None,
    expected_status: str,
    reason: str,
) -> None:
    payload = _request("DIDACTIC")
    if guarantee_type is None:
        payload["mitigators"][0].pop("guarantee_type")
    else:
        payload["mitigators"][0]["guarantee_type"] = guarantee_type
    body = _post(payload)

    assert body["mitigation_status"] == expected_status
    assert reason in body["mitigation_reasons"]
    _assert_no_covered_zero_fpr(body)


@pytest.mark.parametrize(
    ("operation_field", "collateral_field", "collateral_value", "reason"),
    [
        (
            "exposure_indexation_currency",
            "collateral_indexation_currency",
            "USD",
            "indexation_currency_mismatch",
        ),
        (
            "exposure_financial_indexer",
            "collateral_financial_indexer",
            "CDI",
            "financial_indexer_mismatch",
        ),
    ],
)
def test_indexation_mismatch_is_out_of_cut(
    operation_field: str,
    collateral_field: str,
    collateral_value: str,
    reason: str,
) -> None:
    payload = _request("DIDACTIC")
    payload["operation"][operation_field] = "NONE"
    payload["mitigators"][0][collateral_field] = collateral_value
    body = _post(payload)

    assert body["mitigation_status"] == "UNSUPPORTED"
    assert reason in body["mitigation_reasons"]
    _assert_no_covered_zero_fpr(body)


@pytest.mark.parametrize(
    ("operation_field", "collateral_field", "reason"),
    [
        (
            "exposure_indexation_currency",
            "collateral_indexation_currency",
            "missing_indexation_currency",
        ),
        (
            "exposure_financial_indexer",
            "collateral_financial_indexer",
            "missing_financial_indexer",
        ),
    ],
)
def test_absent_indexation_is_not_treated_as_a_match(
    operation_field: str,
    collateral_field: str,
    reason: str,
) -> None:
    payload = _request("DIDACTIC")
    payload["operation"].pop(operation_field)
    payload["mitigators"][0].pop(collateral_field)
    body = _post(payload)

    assert body["mitigation_status"] == "INSUFFICIENT_DATA"
    assert reason in body["mitigation_reasons"]
    _assert_no_covered_zero_fpr(body)


def test_matching_explicit_indexation_is_eligible() -> None:
    payload = _request("DIDACTIC")
    payload["operation"]["exposure_indexation_currency"] = "BRL"
    payload["mitigators"][0]["collateral_indexation_currency"] = "BRL"
    payload["operation"]["exposure_financial_indexer"] = "SELIC"
    payload["mitigators"][0]["collateral_financial_indexer"] = "SELIC"
    body = _post(payload)

    assert body["mitigation_status"] == "CALCULATED"
    assert body["tranches"][0]["fpr"] == "0"


def test_declared_previous_business_day_is_eligible() -> None:
    body = _post(
        _request(
            "DIDACTIC",
            market_value_as_of="2026-09-29",
            market_value_date_policy="PREVIOUS_BUSINESS_DAY_DECLARED",
        )
    )

    assert body["mitigation_status"] == "CALCULATED"
    assert body["tranches"][0]["fpr"] == "0"


@pytest.mark.parametrize(
    ("changes", "expected_status", "reason"),
    [
        (
            {"market_value_as_of": "2026-09-29"},
            "REQUIRES_REVIEW",
            "market_value_not_on_reference_date",
        ),
        (
            {"market_value_as_of": "2026-10-01"},
            "INVALID_INPUT",
            "market_value_after_reference_date",
        ),
        (
            {"market_value_date_policy": None},
            "INSUFFICIENT_DATA",
            "missing_market_value_date_policy",
        ),
    ],
)
def test_invalid_or_missing_market_value_date_never_receives_zero_fpr(
    changes: dict[str, object],
    expected_status: str,
    reason: str,
) -> None:
    payload = _request("DIDACTIC")
    for field, value in changes.items():
        if value is None:
            payload["mitigators"][0].pop(field)
        else:
            payload["mitigators"][0][field] = value
    body = _post(payload)

    assert body["mitigation_status"] == expected_status
    assert reason in body["mitigation_reasons"]
    _assert_no_covered_zero_fpr(body)


@pytest.mark.parametrize(
    ("target", "field", "value", "expected_status", "reason"),
    [
        ("context", "prudential_scope_status", None, "INSUFFICIENT_DATA", "missing_prudential_scope"),
        (
            "context",
            "simple_approach_uniform_use_status",
            "NOT_UNIFORM",
            "UNSUPPORTED",
            "simple_approach_not_used_uniformly",
        ),
        (
            "context",
            "simple_approach_election_date",
            "2026-02-01",
            "REQUIRES_REVIEW",
            "simple_approach_elected_after_fiscal_year_start",
        ),
        (
            "context",
            "fiscal_year_start",
            None,
            "INSUFFICIENT_DATA",
            "missing_simple_approach_dates",
        ),
        ("context", "uses_sa_ccr", True, "UNSUPPORTED", "sa_ccr_out_of_cut"),
        (
            "context",
            "uses_sa_ccr",
            None,
            "INSUFFICIENT_DATA",
            "missing_sa_ccr_declaration",
        ),
        (
            "context",
            "mitigation_recognition_bar_status",
            "BARRED",
            "NOT_APPLICABLE",
            "mitigation_recognition_barred",
        ),
        (
            "context",
            "mitigation_recognition_bar_status",
            "UNKNOWN",
            "REQUIRES_REVIEW",
            "unknown_mitigation_recognition_bar",
        ),
        (
            "mitigator",
            "collateral_provider_type",
            "OTHER",
            "UNSUPPORTED",
            "collateral_provider_out_of_cut",
        ),
        (
            "mitigator",
            "collateral_provider_type",
            None,
            "INSUFFICIENT_DATA",
            "missing_collateral_provider",
        ),
        (
            "mitigator",
            "mark_to_market_consistency_status",
            None,
            "INSUFFICIENT_DATA",
            "missing_mark_consistency_declaration",
        ),
        (
            "mitigator",
            "mark_to_market_consistency_status",
            "NOT_MET",
            "NOT_APPLICABLE",
            "market_value_not_consistent",
        ),
    ],
)
def test_simple_approach_declarations_gate_zero_fpr(
    target: str,
    field: str,
    value: object,
    expected_status: str,
    reason: str,
) -> None:
    payload = _request("DIDACTIC")
    record = payload["context"] if target == "context" else payload["mitigators"][0]
    if value is None:
        record.pop(field)
    else:
        record[field] = value
    body = _post(payload)

    assert body["mitigation_status"] == expected_status
    assert reason in body["mitigation_reasons"]
    _assert_no_covered_zero_fpr(body)


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


def _assert_no_covered_zero_fpr(body: dict[str, object]) -> None:
    assert body["tranches"] == []
    assert "CIRC3809_SIMPLE_TPF_BRL" not in {
        item["rule_id"] for item in body["applied_rules"]
    }


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
        "market_value_date_policy": "REFERENCE_DATE",
        "mark_to_market_consistency_status": "DECLARED",
        "collateral_effective_maturity_date": "2028-09-30",
        "collateral_provider_type": "COUNTERPARTY",
        "collateral_indexation_currency": "NONE",
        "collateral_financial_indexer": "NONE",
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
            "prudential_scope_status": "RWA_CPAD",
            "fiscal_year_start": "2026-01-01",
            "simple_approach_election_date": "2025-12-31",
            "simple_approach_uniform_use_status": "DECLARED_UNIFORM",
            "mitigation_recognition_bar_status": "NOT_BARRED",
            "uses_sa_ccr": False,
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
            "is_otc_derivative": False,
            "exposure_indexation_currency": "NONE",
            "exposure_financial_indexer": "NONE",
        },
        "mitigators": [mitigator],
    }
