"""Regras e fontes visíveis no manifesto, sem promover status."""

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_CUT_SOURCES = ("BCB229", "CIRC3809", "CMN4958")


def visible_rules() -> list[dict[str, str | None]]:
    catalog = yaml.safe_load((_ROOT / "regulations/catalog.yaml").read_text(encoding="utf-8"))
    return [
        {
            "rule_id": rule["rule_id"],
            "status": rule["status"],
            "source_id": rule.get("source_id"),
            "source_sha256": rule.get("source_sha256"),
        }
        for rule in catalog["rules"]
    ]


def visible_sources() -> list[dict[str, str]]:
    index = yaml.safe_load((_ROOT / "regulations/source_index.yaml").read_text(encoding="utf-8"))
    return [
        {
            "id": source["id"],
            "sha256": source["sha256"],
            "archived_file": source["archived_file"],
        }
        for source in index["sources"]
        if source["id"] in _CUT_SOURCES
    ]
