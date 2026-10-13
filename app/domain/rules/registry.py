"""Catálogo cartorial. Metadados preenchidos não liberam execução."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from app.core.security import hash_file


class RuleStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    status: RuleStatus
    effective_from: date | None
    effective_to: date | None
    reviewed_by: str | None
    reviewed_at: date | None
    source_sha256: str | None
    specification: str | None
    source_id: str | None = None
    source_file: str | None = None
    specification_sha256: str | None = None
    required_tests: tuple[str, ...] = ()
    test_report: str | None = None

    def execution_blockers(self, reference_date: date, *, project_root: Path) -> tuple[str, ...]:
        """Exige aprovação, vigência, hashes reais e testes vinculados às fontes."""
        blockers: list[str] = []
        if self.status is not RuleStatus.APPROVED:
            blockers.append("status_not_approved")
        if not self.reviewed_by:
            blockers.append("missing_reviewer")
        if self.reviewed_at is None:
            blockers.append("missing_review_date")
        if self.effective_from is None:
            blockers.append("missing_effective_from")
        elif reference_date < self.effective_from:
            blockers.append("before_effective_date")
        if self.effective_to is not None and reference_date > self.effective_to:
            blockers.append("after_effective_date")

        source_path = _resolve_source_path(self, project_root)
        actual_source_hash = _hash_or_blocker(source_path, blockers, missing_code="missing_source")
        if actual_source_hash is not None and actual_source_hash != self.source_sha256:
            blockers.append("source_hash_mismatch")

        specification_path = _resolve_project_path(self.specification, project_root)
        actual_spec_hash = _hash_or_blocker(
            specification_path,
            blockers,
            missing_code="missing_specification",
        )
        if actual_spec_hash is not None and actual_spec_hash != self.specification_sha256:
            blockers.append("specification_hash_mismatch")

        if not self.required_tests:
            blockers.append("missing_required_tests")
        _check_test_report(
            self,
            project_root,
            blockers,
            source_sha256=actual_source_hash,
            specification_sha256=actual_spec_hash,
        )
        return tuple(blockers)


def load_catalog(path: Path | None = None) -> tuple[RuleDefinition, ...]:
    catalog_path = path or _default_root() / "regulations/catalog.yaml"
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    return tuple(_parse_rule(item) for item in payload.get("rules", ()))


def get_executable_rule(
    rule_id: str,
    reference_date: date,
    *,
    catalog_path: Path | None = None,
    project_root: Path | None = None,
) -> RuleDefinition | None:
    """Retorna a regra somente quando integridade, aprovação e testes fecham."""
    root = project_root or _default_root()
    for rule in load_catalog(catalog_path):
        if rule.rule_id == rule_id and not rule.execution_blockers(reference_date, project_root=root):
            return rule
    return None


def _default_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _parse_rule(item: dict[str, Any]) -> RuleDefinition:
    required_tests = item.get("required_tests") or ()
    return RuleDefinition(
        rule_id=str(item["rule_id"]),
        status=RuleStatus(item["status"]),
        effective_from=_parse_date(item.get("effective_from")),
        effective_to=_parse_date(item.get("effective_to")),
        reviewed_by=item.get("reviewed_by"),
        reviewed_at=_parse_date(item.get("reviewed_at")),
        source_sha256=item.get("source_sha256"),
        specification=item.get("specification"),
        source_id=item.get("source_id"),
        source_file=item.get("source_file"),
        specification_sha256=item.get("specification_sha256"),
        required_tests=tuple(str(test_id) for test_id in required_tests),
        test_report=item.get("test_report"),
    )


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _resolve_source_path(rule: RuleDefinition, project_root: Path) -> Path | None:
    if rule.source_file:
        return _resolve_project_path(rule.source_file, project_root)
    if not rule.source_id:
        return None
    index_path = project_root / "regulations/source_index.yaml"
    if not index_path.is_file():
        return None
    index = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    for source in index.get("sources", ()):
        if source.get("id") == rule.source_id and source.get("archived_file"):
            return _resolve_project_path(str(source["archived_file"]), project_root)
    return None


def _resolve_project_path(value: str | None, project_root: Path) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return None
    root = project_root.resolve()
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        return None
    return resolved


def _hash_or_blocker(path: Path | None, blockers: list[str], *, missing_code: str) -> str | None:
    if path is None or not path.is_file():
        blockers.append(missing_code)
        return None
    return hash_file(path)


def _check_test_report(
    rule: RuleDefinition,
    project_root: Path,
    blockers: list[str],
    *,
    source_sha256: str | None,
    specification_sha256: str | None,
) -> None:
    report_path = _resolve_project_path(rule.test_report, project_root)
    if report_path is None or not report_path.is_file():
        blockers.append("missing_test_report")
        return
    report = yaml.safe_load(report_path.read_text(encoding="utf-8")) or {}
    if report.get("rule_id") != rule.rule_id:
        blockers.append("test_report_rule_mismatch")
    if source_sha256 is None or report.get("source_sha256") != source_sha256:
        blockers.append("test_report_source_mismatch")
    if specification_sha256 is None or report.get("specification_sha256") != specification_sha256:
        blockers.append("test_report_specification_mismatch")
    results = report.get("results") or {}
    if any(results.get(test_id) is not True for test_id in rule.required_tests):
        blockers.append("required_test_not_passed")
