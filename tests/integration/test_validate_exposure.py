"""Validação HTTP de uma exposição sem executar cálculos regulatórios."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def valid_payload():
    return {
        "context": {
            "schema_version": "combined_v1",
            "reference_date": "2026-09-30",
            "institution_profile": "PROFILE_AWAITING_REVIEW",
            "capital_regime": "STANDARDIZED_CREDIT_REVIEW_REQUIRED",
            "collateral_approach": "SIMPLE",
            "rule_set_version": "pending",
            "calculation_mode": "VALIDATION_ONLY",
            "reporting_currency": "BRL",
            "strict_mode": True,
        },
        "operation": {
            "operation_id": "00012345",
            "exposure_id": "EXP-12345",
            "product_type": "SYNTHETIC_CREDIT",
            "balance_amount": "100000.00",
            "currency": "BRL",
            "has_guarantee": True,
            "is_off_balance": False,
        },
        "mitigators": [
            {
                "mitigator_id": "G-01",
                "linked_operation_id": "00012345",
                "guarantee_type": "FINANCIAL_COLLATERAL",
                "guarantee_face_value": "30000.00",
                "guarantee_currency": "BRL",
                "eligibility_evidence_status": "UNKNOWN",
            },
            {
                "mitigator_id": "G-02",
                "linked_operation_id": "00012345",
                "guarantee_type": "FINANCIAL_COLLATERAL",
                "guarantee_face_value": "20000.00",
                "guarantee_currency": "BRL",
                "eligibility_evidence_status": "UNKNOWN",
            },
        ],
    }


def assert_has_no_regulatory_numbers(body):
    forbidden = {
        "fpr_original",
        "rwa_before_mitigation",
        "rwa_after_mitigation",
        "minimum_pr_contribution",
    }
    assert forbidden.isdisjoint(body)


def test_valid_payload_returns_a_structural_report(valid_payload):
    response = client.post("/api/v1/validate/exposure", json=valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["operation_id"] == "00012345"
    assert body["mitigator_count"] == 2
    assert body["issues"] == []
    assert body["regulatory_calculation"] is False
    assert_has_no_regulatory_numbers(body)


def test_regulatory_label_does_not_trigger_calculation(valid_payload):
    valid_payload["context"]["calculation_mode"] = "REGULATORY"

    response = client.post("/api/v1/validate/exposure", json=valid_payload)

    assert response.status_code == 200
    assert response.json()["regulatory_calculation"] is False
    assert_has_no_regulatory_numbers(response.json())


@pytest.mark.parametrize(
    ("path", "invalid_value"),
    [
        (("operation", "operation_id"), 12345),
        (("operation", "balance_amount"), 100000.00),
    ],
)
def test_invalid_scalar_returns_safe_422(valid_payload, path, invalid_value):
    payload = deepcopy(valid_payload)
    payload[path[0]][path[1]] = invalid_value

    response = client.post(
        "/api/v1/validate/exposure",
        json=payload,
        headers={"X-Correlation-ID": "test-correlation"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_SCHEMA"
    assert body["correlation_id"] == "test-correlation"
    assert path[1] in body["details"][0]["loc"]
    assert "traceback" not in response.text.lower()


def test_missing_required_field_returns_safe_422(valid_payload):
    del valid_payload["operation"]["balance_amount"]

    response = client.post("/api/v1/validate/exposure", json=valid_payload)

    assert response.status_code == 422
    assert "balance_amount" in response.json()["details"][0]["loc"]
    assert "traceback" not in response.text.lower()


def test_guarantee_flag_mismatch_is_a_structural_issue(valid_payload):
    valid_payload["mitigators"] = []

    response = client.post("/api/v1/validate/exposure", json=valid_payload)

    assert response.status_code == 200
    assert response.json()["issues"][0]["code"] == "FLAG_RELATION_MISMATCH"


def test_orphan_guarantee_is_a_structural_issue(valid_payload):
    valid_payload["mitigators"][0]["linked_operation_id"] = "OTHER"

    response = client.post("/api/v1/validate/exposure", json=valid_payload)

    assert response.status_code == 200
    assert response.json()["issues"][0]["code"] == "ORPHAN_GUARANTEE"


def test_openapi_lists_only_the_implemented_phase_one_routes():
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/info" in paths
    assert "/api/v1/validate/exposure" in paths
    assert "/api/v1/batches" in paths
    assert "/api/v1/calculations/exposure" not in paths
