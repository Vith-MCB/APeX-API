"""Resumo estrutural do lote, sem grandeza prudencial."""

import json
from pathlib import Path


def write_validation_summary(path: Path, summary: dict) -> None:
    path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
