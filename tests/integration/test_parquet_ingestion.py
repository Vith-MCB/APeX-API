"""Upload de Parquet sintético e rejeição de arquivo inválido."""

import hashlib
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.ingestion.fixture_loader import jsonl_to_parquet
from app.main import app

client = TestClient(app)
ROOT = Path(__file__).parents[2]
CONTEXT = (ROOT / "examples/calculation_context.json").read_text(encoding="utf-8")


def _parquet(tmp_path):
    destination = tmp_path / "combined.parquet"
    jsonl_to_parquet(ROOT / "examples/combined_input.jsonl", destination)
    return destination


def test_valid_parquet_reports_links_without_calculation(tmp_path):
    parquet_path = _parquet(tmp_path)
    with parquet_path.open("rb") as handle:
        response = client.post(
            "/api/v1/validate/parquet",
            data={"context": CONTEXT},
            files={"file": ("combined.parquet", handle, "application/octet-stream")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["operation_count"] == 1
    assert body["exposure_count"] == 1
    assert body["mitigator_count"] == 2
    assert body["balance_total"] == "100000.00"
    assert body["links"] == [
        {
            "operation_id": "00012345",
            "exposure_id": "EXP-12345",
            "mitigator_ids": ["G-01", "G-02"],
        }
    ]
    assert body["input_sha256"] == hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    assert body["issues"] == []
    assert body["regulatory_calculation"] is False
    assert "rwa_before_mitigation" not in body
    assert "rwa_after_mitigation" not in body
    assert "minimum_pr_contribution" not in body
    assert "traceback" not in response.text.lower()


def test_invalid_file_returns_400_without_traceback():
    response = client.post(
        "/api/v1/validate/parquet",
        data={"context": CONTEXT},
        files={"file": ("bad.parquet", b"PK\x03\x04not-parquet", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SCHEMA"
    assert "traceback" not in response.text.lower()


def test_oversized_file_returns_413(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.validation.get_settings",
        lambda: Settings(max_upload_bytes=8),
    )
    with _parquet(tmp_path).open("rb") as handle:
        response = client.post(
            "/api/v1/validate/parquet",
            data={"context": CONTEXT},
            files={"file": ("combined.parquet", handle, "application/octet-stream")},
        )

    assert response.status_code == 413
    assert "traceback" not in response.text.lower()


def test_invalid_context_returns_422(tmp_path):
    with _parquet(tmp_path).open("rb") as handle:
        response = client.post(
            "/api/v1/validate/parquet",
            data={"context": "not-json"},
            files={"file": ("combined.parquet", handle, "application/octet-stream")},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SCHEMA"
    assert "traceback" not in response.text.lower()


def test_script_writes_the_example_outside_the_repository(tmp_path):
    destination = tmp_path / "generated.parquet"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/generate_synthetic_data.py",
            "examples/combined_input.jsonl",
            str(destination),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert Path(completed.stdout.strip()) == destination
    assert destination.is_file()
