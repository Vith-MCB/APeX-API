"""Guardas cartoriais: evidência em revisão nunca vira resultado prudencial."""

from datetime import date
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.core.security import hash_file
from app.domain.rules.registry import RuleDefinition, RuleStatus, get_executable_rule, load_catalog
from app.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_catalog_has_no_approved_rule() -> None:
    rules = load_catalog()

    assert rules
    assert all(rule.status is not RuleStatus.APPROVED for rule in rules)
    assert all(rule.reviewed_by is None and rule.reviewed_at is None for rule in rules)


def test_draft_and_in_review_rules_are_not_executable() -> None:
    rules = load_catalog()

    for rule in rules:
        assert rule.status in {RuleStatus.DRAFT, RuleStatus.IN_REVIEW}
        assert get_executable_rule(rule.rule_id, date(2026, 9, 30)) is None


def test_off_balance_exposure_remains_without_regulatory_numbers() -> None:
    response = TestClient(app).post(
        "/api/v1/validate/exposure",
        json={
            "context": {
                "schema_version": "combined_v1",
                "reference_date": "2026-09-30",
                "institution_profile": "UNDEFINED",
                "capital_regime": "UNDEFINED",
                "collateral_approach": "SIMPLE",
                "rule_set_version": "0.1.0",
                "calculation_mode": "REGULATORY",
                "reporting_currency": "BRL",
                "strict_mode": True,
            },
            "operation": {
                "operation_id": "OP-OFF-BALANCE",
                "exposure_id": "EXP-OFF-BALANCE",
                "product_type": "SYNTHETIC",
                "balance_amount": "100000.00",
                "currency": "BRL",
                "has_guarantee": False,
                "is_off_balance": True,
            },
            "mitigators": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["regulatory_calculation"] is False
    assert {"fpr", "rwa", "capital_contribution"}.isdisjoint(body)


def test_archived_sources_match_registered_hashes() -> None:
    index = yaml.safe_load(
        (ROOT / "regulations/source_index.yaml").read_text(encoding="utf-8")
    )
    archived_sources = [source for source in index["sources"] if source.get("archived_file")]

    assert {source["id"] for source in archived_sources} == {"BCB229", "CIRC3809", "CMN4958"}
    for source in archived_sources:
        assert hash_file(ROOT / source["archived_file"]) == source["sha256"]
        for supporting_file in source.get("supporting_files", ()):
            assert (
                hash_file(ROOT / supporting_file["archived_file"])
                == supporting_file["sha256"]
            )


def test_sources_are_adequate_for_reference_date() -> None:
    index = yaml.safe_load(
        (ROOT / "regulations/source_index.yaml").read_text(encoding="utf-8")
    )
    archived_sources = [source for source in index["sources"] if source.get("archived_file")]

    for source in archived_sources:
        reference_date = date.fromisoformat(source["reference_date_checked"])
        basis_date = date.fromisoformat(
            source.get("version_date") or source["latest_effective_update"]
        )
        assert reference_date == date(2026, 9, 30)
        assert source["status_on_reference_date"] == "Vigente"
        assert basis_date <= reference_date


def test_catalog_references_complete_review_artifacts() -> None:
    catalog = yaml.safe_load(
        (ROOT / "regulations/catalog.yaml").read_text(encoding="utf-8")
    )
    source_index = yaml.safe_load(
        (ROOT / "regulations/source_index.yaml").read_text(encoding="utf-8")
    )
    source_hashes = {
        source["id"]: source["sha256"]
        for source in source_index["sources"]
        if source.get("sha256")
    }
    review_rules = [rule for rule in catalog["rules"] if rule["status"] == "IN_REVIEW"]

    assert {rule["rule_id"] for rule in review_rules} == {
        "BCB229_ART36_PJ_NAO_FINANCEIRA",
        "CIRC3809_SIMPLE_TPF_BRL",
    }
    for rule in review_rules:
        assert ROOT.joinpath(rule["specification"]).is_file()
        assert ROOT.joinpath(rule["requirements_matrix"]).is_file()
        assert ROOT.joinpath(rule["contract_attributes"]).is_file()
        assert rule["source_sha256"] == source_hashes[rule["source_id"]]
        assert rule["reviewed_by"] is None
        assert rule["reviewed_at"] is None


def test_requirement_matrix_covers_selected_provisions() -> None:
    matrix = yaml.safe_load(
        (ROOT / "regulations/specifications/REQUIREMENTS_EVIDENCE_MATRIX.yaml").read_text(
            encoding="utf-8"
        )
    )
    requirement_ids = {requirement["id"] for requirement in matrix["requirements"]}

    assert matrix["status"] == "IN_REVIEW"
    assert matrix["reference_date"] == "2026-09-30"
    assert {"BCB229-ART36-CAPUT", "BCB229-ART36-PARAGRAFO-UNICO"} <= requirement_ids
    assert any(identifier.startswith("BCB229-ART46") for identifier in requirement_ids)
    for article in range(2, 8):
        assert any(
            identifier.startswith(f"CIRC3809-ART{article}") for identifier in requirement_ids
        )
    assert matrix["responsibility_model"]["apex_audits_institution_documents"] is False
    serialized = yaml.safe_dump(matrix)
    assert "LEGAL_OPINION" not in serialized
    assert "document_sha256" not in serialized


def test_draft_and_in_review_remain_blocked_with_complete_metadata(tmp_path: Path) -> None:
    for status in ("DRAFT", "IN_REVIEW"):
        catalog, root = _approval_package(tmp_path / status, status=status)
        rule = load_catalog(catalog)[0]

        assert get_executable_rule("RULE-CUT", date(2026, 9, 30), catalog_path=catalog, project_root=root) is None
        assert "status_not_approved" in rule.execution_blockers(date(2026, 9, 30), project_root=root)


def test_approved_without_reviewer_does_not_execute(tmp_path: Path) -> None:
    catalog, root = _approval_package(tmp_path, reviewed_by="")
    rule = load_catalog(catalog)[0]

    assert "missing_reviewer" in rule.execution_blockers(date(2026, 9, 30), project_root=root)
    assert get_executable_rule("RULE-CUT", date(2026, 9, 30), catalog_path=catalog, project_root=root) is None


def test_approved_metadata_without_integrity_does_not_execute(tmp_path: Path) -> None:
    catalog, root = _approval_package(tmp_path, source_sha256="0" * 64, specification_sha256="1" * 64)
    rule = load_catalog(catalog)[0]
    blockers = rule.execution_blockers(date(2026, 9, 30), project_root=root)

    assert get_executable_rule("RULE-CUT", date(2026, 9, 30), catalog_path=catalog, project_root=root) is None
    assert "source_hash_mismatch" in blockers
    assert "specification_hash_mismatch" in blockers


def test_approved_rule_outside_effective_period_does_not_execute(tmp_path: Path) -> None:
    catalog, root = _approval_package(tmp_path, effective_to="2026-09-29")
    rule = load_catalog(catalog)[0]

    assert "before_effective_date" in rule.execution_blockers(date(2023, 6, 30), project_root=root)
    assert "after_effective_date" in rule.execution_blockers(date(2026, 9, 30), project_root=root)
    assert get_executable_rule("RULE-CUT", date(2026, 9, 30), catalog_path=catalog, project_root=root) is None


def test_approved_rule_with_failed_required_test_does_not_execute(tmp_path: Path) -> None:
    catalog, root = _approval_package(tmp_path, tests_passed=False)
    rule = load_catalog(catalog)[0]

    assert "required_test_not_passed" in rule.execution_blockers(date(2026, 9, 30), project_root=root)
    assert get_executable_rule("RULE-CUT", date(2026, 9, 30), catalog_path=catalog, project_root=root) is None


def test_approved_rule_executes_only_after_integrity_and_tests(tmp_path: Path) -> None:
    catalog, root = _approval_package(tmp_path)

    assert isinstance(
        get_executable_rule("RULE-CUT", date(2026, 9, 30), catalog_path=catalog, project_root=root),
        RuleDefinition,
    )


def _approval_package(
    directory: Path,
    *,
    status: str = "APPROVED",
    reviewed_by: str = "Vitor",
    source_sha256: str | None = None,
    specification_sha256: str | None = None,
    effective_to: str | None = None,
    tests_passed: bool = True,
) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "source.txt"
    specification = directory / "specification.md"
    report = directory / "tests.yaml"
    source.write_text("fonte oficial sintética\n", encoding="utf-8")
    specification.write_text("ficha sintética\n", encoding="utf-8")
    actual_source_hash = hash_file(source)
    actual_spec_hash = hash_file(specification)
    report.write_text(
        yaml.safe_dump(
            {
                "rule_id": "RULE-CUT",
                "source_sha256": actual_source_hash,
                "specification_sha256": actual_spec_hash,
                "results": {"tests/regulatory/test_cut.py::test_case": tests_passed},
            }
        ),
        encoding="utf-8",
    )
    catalog = directory / "catalog.yaml"
    catalog.write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "rule_id": "RULE-CUT",
                        "status": status,
                        "effective_from": "2023-07-01",
                        "effective_to": effective_to,
                        "reviewed_by": reviewed_by,
                        "reviewed_at": "2026-10-12",
                        "source_file": "source.txt",
                        "source_sha256": source_sha256 or actual_source_hash,
                        "specification": "specification.md",
                        "specification_sha256": specification_sha256 or actual_spec_hash,
                        "required_tests": ["tests/regulatory/test_cut.py::test_case"],
                        "test_report": "tests.yaml",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return catalog, directory
