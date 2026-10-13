"""O harness de benchmark mede um lote pequeno sem publicar número prudencial."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_small_structural_benchmark_records_real_elapsed_time(tmp_path: Path) -> None:
    destination = tmp_path / "results.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/benchmark.py"),
            "--sizes",
            "32",
            "--repeats",
            "1",
            "--no-million",
            "--output",
            str(destination),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["workload"] == "structural_validation_and_export"
    assert payload["didactic_calculation"] is False
    run = payload["runs"][0]
    assert run["rows"] == 32
    assert run["generation_seconds"] >= 0
    assert run["total_seconds"] > 0
    assert run["validation_seconds"] >= 0
    assert run["export_seconds"] >= 0
    assert run["rows_per_second"] > 0
    assert run["rss_kib"] > 0
    assert run["input_bytes"] > 0
    assert run["calculated_subset_rwa"] is None
    assert run["status"] == "COMPLETED"
    assert "error" not in run
