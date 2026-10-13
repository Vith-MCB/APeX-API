"""Cálculo individual do FPR original. O modo regulatório permanece bloqueado."""

from decimal import Decimal

from fastapi import APIRouter

from app.core.money import parse_decimal, quantize_money
from app.domain.rules.bcb229 import Art36Input
from app.domain.services.fpr import resolve_original_fpr
from app.schemas.calculations import ExposureCalculationReport, ValidateExposureRequest

router = APIRouter(prefix="/calculations", tags=["calculations"])


@router.post("/exposure", response_model=ExposureCalculationReport)
def calculate_exposure(request: ValidateExposureRequest) -> ExposureCalculationReport:
    decision = resolve_original_fpr(
        _art36_input(request),
        request.context.calculation_mode,
    )
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


def _optional_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return parse_decimal(value)


def _money_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(quantize_money(value, 2), "f")
