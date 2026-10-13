"""Cálculo individual do FPR original. O modo regulatório permanece bloqueado."""

from decimal import Decimal

from fastapi import APIRouter

from app.core.enums import CalculationMode, CalculationStatus
from app.core.money import parse_decimal, quantize_money
from app.domain.rules.bcb229 import Art36Input
from app.domain.rules.circ3809 import CollateralInput
from app.domain.services.fpr import resolve_original_fpr
from app.domain.services.tranche_builder import resolve_simple_collateral
from app.schemas.calculations import (
    ExposureCalculationReport,
    TrancheReport,
    ValidateExposureRequest,
)
from app.schemas.mitigators import MitigatorInput

router = APIRouter(prefix="/calculations", tags=["calculations"])


@router.post("/exposure", response_model=ExposureCalculationReport)
def calculate_exposure(request: ValidateExposureRequest) -> ExposureCalculationReport:
    art36 = _art36_input(request)
    decision = resolve_original_fpr(art36, request.context.calculation_mode)
    candidate = decision
    if request.context.calculation_mode is not CalculationMode.DIDACTIC:
        candidate = resolve_original_fpr(art36, CalculationMode.DIDACTIC)
    mitigation = resolve_simple_collateral(
        mode=request.context.calculation_mode,
        reference_date=request.context.reference_date,
        operation_id=request.operation.operation_id,
        currency=request.operation.currency,
        exposure_indexer=request.operation.exposure_indexer,
        exposure_maturity=request.operation.exposure_effective_maturity_date,
        original=candidate,
        mitigators=tuple(_collateral_input(item) for item in request.mitigators),
    )
    publish = mitigation.status is CalculationStatus.CALCULATED
    tranches = [
        TrancheReport(
            tranche_type=tranche.tranche_type,
            amount=_money_text(tranche.amount) or "0.00",
            fpr=format(tranche.fpr, "f"),
            rule_id=tranche.rule_id,
            article=tranche.article,
        )
        for tranche in mitigation.tranches
    ]
    return ExposureCalculationReport(
        exposure_id=request.operation.exposure_id,
        operation_id=request.operation.operation_id,
        calculation_mode=request.context.calculation_mode,
        reference_date=request.context.reference_date,
        calculation_status=decision.status,
        rule_id=decision.rule_id,
        article=decision.article,
        exposure_amount=_money_text(decision.exposure_amount),
        original_fpr=None if decision.original_fpr is None else format(decision.original_fpr, "f"),
        reasons=list(decision.reasons),
        issues=list(decision.issues),
        mitigator_ids=list(mitigation.mitigator_ids),
        mitigation_status=mitigation.status,
        mitigation_reasons=list(mitigation.reasons),
        tranches=tranches if publish else [],
        didactic_not_regulatory=decision.didactic_not_regulatory,
    )


def _art36_input(request: ValidateExposureRequest) -> Art36Input:
    operation = request.operation
    return Art36Input(
        reference_date=request.context.reference_date,
        is_off_balance=operation.is_off_balance,
        counterparty_legal_nature=operation.counterparty_legal_nature,
        counterparty_is_financial=operation.counterparty_is_financial,
        total_assets=_optional_decimal(operation.counterparty_total_assets),
        annual_gross_revenue=_optional_decimal(operation.counterparty_annual_gross_revenue),
        financial_year_end=operation.counterparty_financial_year_end,
        financial_data_is_latest_available=operation.financial_data_is_latest_available,
        prudential_category_conflict_status=operation.prudential_category_conflict_status,
        balance_amount=parse_decimal(operation.balance_amount),
        provided_exposure_amount=_optional_decimal(operation.provided_exposure_amount),
        exposure_value_basis=operation.exposure_value_basis,
        provided_fpr=_optional_decimal(operation.provided_fpr),
    )


def _collateral_input(item: MitigatorInput) -> CollateralInput:
    return CollateralInput(
        mitigator_id=item.mitigator_id,
        linked_operation_id=item.linked_operation_id,
        collateral_subtype=item.collateral_subtype,
        market_value=_optional_decimal(item.collateral_market_value),
        currency=item.guarantee_currency,
        collateral_indexer=item.collateral_indexer,
        market_value_as_of=item.market_value_as_of,
        mark_to_market_frequency=item.mark_to_market_frequency,
        effective_maturity_date=item.collateral_effective_maturity_date,
        overlap_status=item.overlap_status,
        association_scope=item.association_scope,
        institution_requirements_status=item.institution_requirements_status,
    )


def _optional_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return parse_decimal(value)


def _money_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(quantize_money(value, 2), "f")
