"""Manifesto com o hash calculado na entrada."""

import json
from pathlib import Path


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
