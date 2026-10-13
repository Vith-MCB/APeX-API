"""Enquadramento do art. 36 a partir de declarações estruturadas."""

from app.core.enums import (
    CalculationStatus,
    CounterpartyLegalNature,
    PrudentialCategoryConflictStatus,
)
from app.domain.rules.bcb229 import (
    EFFECTIVE_FROM,
    GROSS_REVENUE_LIMIT,
    RETAIL_REVENUE_LIMIT,
    TOTAL_ASSETS_LIMIT,
    Art36Input,
)


def classify_article_36(data: Art36Input) -> tuple[CalculationStatus, tuple[str, ...]]:
    """Retorna CALCULATED somente quando o recorte declarado está completo."""
    if data.reference_date < EFFECTIVE_FROM:
        return CalculationStatus.UNSUPPORTED, ("before_effective_date",)
    if data.is_off_balance:
        return CalculationStatus.UNSUPPORTED, ("off_balance",)
    if _outside_private_counterparty(data):
        return CalculationStatus.UNSUPPORTED, ("counterparty_outside_article_36",)
    if data.prudential_category_conflict_status is PrudentialCategoryConflictStatus.CONFLICT_DECLARED:
        return CalculationStatus.REQUIRES_REVIEW, ("competing_category_declared",)
    if data.annual_gross_revenue is not None and data.annual_gross_revenue < RETAIL_REVENUE_LIMIT:
        return CalculationStatus.UNSUPPORTED, ("retail_route_not_in_cut",)
    if data.total_assets is not None and data.total_assets >= TOTAL_ASSETS_LIMIT:
        return CalculationStatus.NOT_APPLICABLE, ("total_assets_not_below_limit",)
    if data.annual_gross_revenue is not None and data.annual_gross_revenue >= GROSS_REVENUE_LIMIT:
        return CalculationStatus.NOT_APPLICABLE, ("gross_revenue_not_below_limit",)
    if data.financial_year_end is not None and data.financial_year_end > data.reference_date:
        return CalculationStatus.INVALID_INPUT, ("financial_year_after_reference_date",)
    if data.financial_data_is_latest_available is False:
        return CalculationStatus.NOT_APPLICABLE, ("financial_year_not_latest_available",)

    missing = _missing_declarations(data)
    if missing:
        return CalculationStatus.INSUFFICIENT_DATA, missing
    return CalculationStatus.CALCULATED, ("article_36_conditions_met",)


def _outside_private_counterparty(data: Art36Input) -> bool:
    if (
        data.counterparty_legal_nature is not None
        and data.counterparty_legal_nature is not CounterpartyLegalNature.PRIVATE_LEGAL_ENTITY
    ):
        return True
    return data.counterparty_is_financial is True


def _missing_declarations(data: Art36Input) -> tuple[str, ...]:
    missing: list[str] = []
    if data.counterparty_legal_nature is None:
        missing.append("missing_counterparty_legal_nature")
    if data.counterparty_is_financial is None:
        missing.append("missing_counterparty_is_financial")
    if data.total_assets is None:
        missing.append("missing_total_assets")
    if data.annual_gross_revenue is None:
        missing.append("missing_annual_gross_revenue")
    if data.financial_year_end is None:
        missing.append("missing_financial_year_end")
    if data.financial_data_is_latest_available is None:
        missing.append("missing_financial_year_recency")
    if data.prudential_category_conflict_status in {
        None,
        PrudentialCategoryConflictStatus.UNKNOWN,
    }:
        missing.append("missing_category_conflict_declaration")
    return tuple(missing)
