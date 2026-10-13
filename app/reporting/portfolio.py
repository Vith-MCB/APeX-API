"""Agrega o subconjunto calculado e prepara as linhas exportadas."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.enums import CalculationStatus, TrancheType
from app.core.money import quantize_money
from app.domain.models.exposure import Operation
from app.domain.models.mitigator import Mitigator
from app.schemas.calculations import ExposureCalculationReport

_UNRESOLVED = {
    CalculationStatus.UNSUPPORTED,
    CalculationStatus.INSUFFICIENT_DATA,
    CalculationStatus.REQUIRES_REVIEW,
    CalculationStatus.INVALID_INPUT,
}
_RATIO_SCALE = Decimal("0.0000000001")
_COVERAGE_SCALE = Decimal("0.0001")


@dataclass(frozen=True)
class ExposureExport:
    job_id: str
    row_source_id: str
    operation_id: str
    exposure_id: str
    reference_date: date
    calculation_mode: str
    status: str
    rule_set_version: str
    exposure_amount_e: Decimal | None
    fpr_original: Decimal | None
    rwa_before_mitigation: Decimal | None
    rwa_after_mitigation: Decimal | None
    rwa_delta: Decimal | None
    rwa_reduction_amount: Decimal | None
    rwa_reduction_ratio: Decimal | None
    minimum_pr_contribution: Decimal | None
    currency: str
    mitigator_count: int
    tranche_count: int
    issue_codes: str
    trace_ref: str | None
    input_sha256: str
    balance_amount: Decimal


@dataclass(frozen=True)
class TrancheExport:
    exposure_id: str
    tranche_id: str
    mitigator_id: str | None
    tranche_kind: str
    covered_amount: Decimal
    applied_fpr: Decimal
    tranche_rwa: Decimal
    treatment_id: str
    rule_id: str
    rounding_stage: str
    eligibility_status: str
    source_row_id: str
    status: str


@dataclass(frozen=True)
class TraceExport:
    exposure_id: str
    rule_id: str
    article: str
    factor: str


@dataclass(frozen=True)
class IssueExport:
    code: str
    field: str
    message: str
    operation_id: str | None
    exposure_id: str | None
    mitigator_id: str | None
    status: str


def structural_exposure_exports(
    operations: list[Operation],
    mitigators: list[Mitigator],
    *,
    job_id: str,
    calculation_mode: str,
    rule_set_version: str,
    input_sha256: str,
) -> list[ExposureExport]:
    """O layout combined_v1 não carrega o recorte, então não publica número."""
    linked: dict[str, list[Mitigator]] = {}
    for mitigator in mitigators:
        linked.setdefault(mitigator.linked_operation_id, []).append(mitigator)
    rows: list[ExposureExport] = []
    for operation in operations:
        group = linked.get(operation.operation_id, [])
        mismatched = operation.has_guarantee != bool(group)
        rows.append(
            ExposureExport(
                job_id=job_id,
                row_source_id=operation.row_id,
                operation_id=operation.operation_id,
                exposure_id=operation.exposure_id,
                reference_date=operation.reference_date,
                calculation_mode=calculation_mode,
                status=(
                    CalculationStatus.INVALID_INPUT.value
                    if mismatched
                    else CalculationStatus.INSUFFICIENT_DATA.value
                ),
                rule_set_version=rule_set_version,
                exposure_amount_e=None,
                fpr_original=None,
                rwa_before_mitigation=None,
                rwa_after_mitigation=None,
                rwa_delta=None,
                rwa_reduction_amount=None,
                rwa_reduction_ratio=None,
                minimum_pr_contribution=None,
                currency=operation.currency,
                mitigator_count=len(group),
                tranche_count=0,
                issue_codes="FLAG_RELATION_MISMATCH" if mismatched else "",
                trace_ref=None,
                input_sha256=input_sha256,
                balance_amount=operation.balance_amount,
            )
        )
    return rows


def exports_from_calculation(
    report: ExposureCalculationReport,
    *,
    job_id: str,
    row_source_id: str,
    rule_set_version: str,
    input_sha256: str,
    balance_amount: Decimal,
    currency: str,
) -> tuple[ExposureExport, list[TrancheExport], list[TraceExport]]:
    """Converte o relatório didático já calculado em linhas de exportação."""
    before = _decimal(report.rwa_before_mitigation)
    after = _decimal(report.rwa_after_mitigation)
    reduction_amount, reduction_ratio = _reduction(before, after)
    resolved = after is not None
    status = _export_status(report)
    exposure = ExposureExport(
        job_id=job_id,
        row_source_id=row_source_id,
        operation_id=report.operation_id,
        exposure_id=report.exposure_id,
        reference_date=report.reference_date,
        calculation_mode=report.calculation_mode.value,
        status=status,
        rule_set_version=rule_set_version,
        exposure_amount_e=_decimal(report.exposure_amount),
        fpr_original=_decimal(report.original_fpr),
        rwa_before_mitigation=before,
        rwa_after_mitigation=after,
        rwa_delta=_decimal(report.rwa_delta),
        rwa_reduction_amount=reduction_amount,
        rwa_reduction_ratio=reduction_ratio,
        minimum_pr_contribution=_decimal(report.minimum_pr_contribution),
        currency=currency,
        mitigator_count=len(report.mitigator_ids),
        tranche_count=len(report.tranches),
        issue_codes=",".join(issue.code for issue in report.issues),
        trace_ref=report.exposure_id if resolved else None,
        input_sha256=input_sha256,
        balance_amount=balance_amount,
    )
    covered_mitigator = report.mitigator_ids[0] if report.mitigator_ids else None
    tranches = [
        TrancheExport(
            exposure_id=report.exposure_id,
            tranche_id=f"{report.exposure_id}-{index + 1}",
            mitigator_id=(
                None
                if tranche.tranche_type is TrancheType.UNCOVERED
                else covered_mitigator
            ),
            tranche_kind=tranche.tranche_type.value,
            covered_amount=_required_decimal(tranche.amount),
            applied_fpr=_required_decimal(tranche.fpr),
            tranche_rwa=_required_decimal(tranche.rwa_contribution),
            treatment_id=tranche.rule_id,
            rule_id=tranche.rule_id,
            rounding_stage="response_scale_2",
            eligibility_status=CalculationStatus.CALCULATED.value,
            source_row_id=row_source_id,
            status=CalculationStatus.CALCULATED.value,
        )
        for index, tranche in enumerate(report.tranches)
    ]
    traces = (
        [
            TraceExport(
                exposure_id=report.exposure_id,
                rule_id=rule.rule_id,
                article=rule.article,
                factor=rule.factor,
            )
            for rule in report.applied_rules
        ]
        if resolved
        else []
    )
    return exposure, tranches, traces


def aggregate_portfolio(
    results: list[ExposureExport],
    *,
    operation_row_count: int,
    guarantee_row_count: int,
    issue_count: int,
    balance_total: Decimal,
) -> dict[str, object]:
    """Soma RWA e contribuição só onde o RWA posterior foi publicado."""
    included = [row for row in results if row.rwa_after_mitigation is not None]
    pending = [row for row in results if row.rwa_after_mitigation is None]
    contributions = [
        row.minimum_pr_contribution
        for row in included
        if row.minimum_pr_contribution is not None
    ]
    status_counts: dict[str, int] = {}
    for row in results:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
    exposure_count = len(results)
    calculated_count = len(included)
    coverage = (
        Decimal(0)
        if exposure_count == 0
        else Decimal(calculated_count) / Decimal(exposure_count)
    )
    return {
        "operation_count": operation_row_count,
        "exposure_count": exposure_count,
        "mitigator_count": guarantee_row_count,
        "balance_total": _money(balance_total),
        "issue_count": issue_count,
        "complete_regulatory_coverage": False,
        "operation_row_count": operation_row_count,
        "guarantee_row_count": guarantee_row_count,
        "multi_mitigator_operation_count": sum(row.mitigator_count > 1 for row in results),
        "pending_exposure_count": len(pending),
        "pending_balance": _money(sum((row.balance_amount for row in pending), Decimal("0"))),
        "calculated_exposure_count": calculated_count,
        "coverage_ratio": format(coverage.quantize(_COVERAGE_SCALE), "f"),
        "calculated_subset_rwa": _optional_money(
            sum((row.rwa_after_mitigation for row in included), Decimal("0"))
            if included
            else None
        ),
        "calculated_subset_pr_contribution": _optional_money(
            sum(contributions, Decimal("0")) if contributions else None
        ),
        "status_counts": status_counts,
    }


def _export_status(report: ExposureCalculationReport) -> str:
    if report.mitigation_status in _UNRESOLVED:
        return report.mitigation_status.value
    if report.calculation_status is not CalculationStatus.CALCULATED:
        return report.calculation_status.value
    if report.mitigation_status is CalculationStatus.NOT_APPLICABLE:
        return CalculationStatus.NOT_APPLICABLE.value
    return CalculationStatus.CALCULATED.value


def _reduction(
    before: Decimal | None,
    after: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    if before is None or after is None:
        return None, None
    amount = before - after
    if before == 0:
        return amount, None
    return amount, (amount / before).quantize(_RATIO_SCALE)


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def _required_decimal(value: str | None) -> Decimal:
    parsed = _decimal(value)
    if parsed is None:
        return Decimal("0")
    return parsed


def _money(value: Decimal) -> str:
    return format(quantize_money(value, 2), "f")


def _optional_money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _money(value)
