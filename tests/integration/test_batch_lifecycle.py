"""Fila persistida, worker e publicação da validação."""

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.infrastructure.file_store import FileStore, UnsafePath, job_directory
from app.infrastructure.job_repository import JobRepository
from app.ingestion.fixture_loader import write_combined_parquet
from app.main import app
from app.worker.job_runner import run_job, run_once

client = TestClient(app)
ROOT = Path(__file__).parents[2]
CONTEXT = (ROOT / "examples/calculation_context.json").read_text(encoding="utf-8")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path, max_upload_bytes=50_000_000)
    monkeypatch.setattr("app.api.v1.batches.get_settings", lambda: settings)
    monkeypatch.setattr("app.worker.job_runner.get_settings", lambda: settings)
    return settings


def _operation(index, **overrides):
    row = {
        "record_type": "OPERATION",
        "row_id": f"r{index}",
        "operation_id": f"{index:08d}",
        "exposure_id": f"EXP-{index}",
        "reference_date": "2026-09-30",
        "product_type": "SYNTHETIC_CREDIT",
        "balance_amount": "1.00",
        "currency": "BRL",
        "has_guarantee": False,
        "is_off_balance": False,
    }
    row.update(overrides)
    return row


def _upload(tmp_path, rows):
    path = tmp_path / "batch.parquet"
    write_combined_parquet(rows, path)
    with path.open("rb") as handle:
        response = client.post(
            "/api/v1/batches",
            data={"context": CONTEXT},
            files={"file": ("ignored.parquet", handle, "application/octet-stream")},
        )
    return response


def _run_until_done():
    assert run_once() is True
    assert run_once() is False


@pytest.mark.parametrize("row_count", [1_000, 10_000])
def test_synthetic_batch_finishes_with_operation_balance_only(workspace, tmp_path, row_count):
    response = _upload(tmp_path, [_operation(index) for index in range(row_count)])

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.json()["status"] == "PENDING"
    _run_until_done()

    status = client.get(f"/api/v1/batches/{job_id}")
    summary = client.get(f"/api/v1/batches/{job_id}/summary")
    assert status.status_code == 200
    assert status.json()["status"] == "COMPLETED"
    assert summary.status_code == 200
    body = summary.json()
    assert body["operation_count"] == row_count
    assert body["exposure_count"] == row_count
    assert body["mitigator_count"] == 0
    assert body["balance_total"] == f"{row_count}.00"
    assert body["complete_regulatory_coverage"] is False
    assert body["calculated_subset_rwa"] is None
    assert body["calculated_subset_pr_contribution"] is None
    assert body["pending_exposure_count"] == row_count
    assert body["coverage_ratio"] == "0.0000"
    assert "rwa_before_mitigation" not in body
    assert client.get(f"/api/v1/batches/{job_id}/artifacts/results").status_code == 200
    assert client.get(f"/api/v1/batches/{job_id}/artifacts/tranches").status_code == 200
    assert client.get(f"/api/v1/batches/{job_id}/artifacts/trace").status_code == 200
    manifest = client.get(f"/api/v1/batches/{job_id}/artifacts/manifest").json()
    stored = (workspace.data_dir / "input" / job_id / "upload.parquet").read_bytes()
    assert manifest["input_sha256"] == hashlib.sha256(stored).hexdigest()


def test_row_issue_is_reported_and_job_stays_partial(workspace, tmp_path):
    rows = [
        _operation(1, has_guarantee=True),
        {
            "record_type": "GUARANTEE",
            "row_id": "g1",
            "granted_operation": "MISSING",
            "mitigator_id": "G-01",
            "guarantee_type": "FINANCIAL_COLLATERAL",
            "guarantee_face_value": "10.00",
        },
    ]
    response = _upload(tmp_path, rows)
    job_id = response.json()["job_id"]
    _run_until_done()

    assert client.get(f"/api/v1/batches/{job_id}").json()["status"] == "PARTIAL"
    errors = client.get(f"/api/v1/batches/{job_id}/errors")
    assert errors.status_code == 200
    assert errors.json()["issues"][0]["code"] == "ORPHAN_GUARANTEE"
    assert not (workspace.data_dir / "work" / job_id).exists()


def test_expired_running_job_does_not_publish_work_files(workspace, tmp_path):
    response = _upload(tmp_path, [_operation(1)])
    job_id = response.json()["job_id"]
    repository = JobRepository(workspace.database_path)
    assert repository.claim_next_job("test-worker") is not None
    work = workspace.data_dir / "work" / job_id
    work.mkdir(parents=True)
    (work / "partial.parquet").write_bytes(b"incomplete")
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with sqlite3.connect(workspace.database_path) as connection:
        connection.execute("UPDATE jobs SET heartbeat_at = ? WHERE job_id = ?", (old, job_id))

    assert run_once() is False

    assert client.get(f"/api/v1/batches/{job_id}").json()["status"] == "INTERRUPTED"
    assert not (workspace.data_dir / "output" / job_id).exists()
    assert not work.exists()


def test_cancel_before_publish_leaves_no_output(workspace, tmp_path):
    response = _upload(tmp_path, [_operation(1)])
    job_id = response.json()["job_id"]
    repository = JobRepository(workspace.database_path)
    job = repository.claim_next_job("test-worker")
    repository.request_cancel(job_id)

    run_job(job, repository, FileStore(workspace.data_dir), workspace)

    assert repository.get_job(job_id).status == "CANCELLED"
    assert not (workspace.data_dir / "output" / job_id).exists()


def test_only_one_worker_claims_a_job(workspace, tmp_path):
    _upload(tmp_path, [_operation(1)])
    repository = JobRepository(workspace.database_path)

    assert repository.claim_next_job("worker-a") is not None
    assert repository.claim_next_job("worker-b") is None


def test_invalid_upload_does_not_create_a_job(workspace):
    response = client.post(
        "/api/v1/batches",
        data={"context": CONTEXT},
        files={"file": ("bad.parquet", b"not-parquet", "application/octet-stream")},
    )

    assert response.status_code == 400
    if not workspace.database_path.exists():
        return
    with sqlite3.connect(workspace.database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()
    assert count[0] == 0


def test_running_job_cannot_be_deleted(workspace, tmp_path):
    response = _upload(tmp_path, [_operation(1)])
    job_id = response.json()["job_id"]
    JobRepository(workspace.database_path).claim_next_job("test-worker")

    deleted = client.delete(f"/api/v1/batches/{job_id}")

    assert deleted.status_code == 409


def test_path_outside_data_is_rejected(workspace):
    with pytest.raises(UnsafePath):
        job_directory(workspace.data_dir, "input", "../outside")


def test_database_initialization_keeps_existing_jobs(workspace, tmp_path):
    response = _upload(tmp_path, [_operation(1)])
    job_id = response.json()["job_id"]

    again = JobRepository(workspace.database_path)

    assert again.get_job(job_id).status == "PENDING"
