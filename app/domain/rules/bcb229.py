"""Recorte do art. 36 da Resolução BCB 229, sem cálculo de RWA."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.enums import CounterpartyLegalNature, ExposureValueBasis, PrudentialCategoryConflictStatus

RULE_ID = "BCB229_ART36_PJ_NAO_FINANCEIRA"
ARTICLE = "36"
EFFECTIVE_FROM = date(2023, 7, 1)
ORIGINAL_FPR = Decimal("0.85")
RETAIL_REVENUE_LIMIT = Decimal("15000000.00")
TOTAL_ASSETS_LIMIT = Decimal("240000000.00")
GROSS_REVENUE_LIMIT = Decimal("300000000.00")


@dataclass(frozen=True)
class Art36Input:
    reference_date: date
    is_off_balance: bool
    counterparty_legal_nature: CounterpartyLegalNature | None
    counterparty_is_financial: bool | None
    total_assets: Decimal | None
    annual_gross_revenue: Decimal | None
    financial_year_end: date | None
    financial_data_is_latest_available: bool | None
    prudential_category_conflict_status: PrudentialCategoryConflictStatus | None
    balance_amount: Decimal
    provided_exposure_amount: Decimal | None
    exposure_value_basis: ExposureValueBasis | None
    provided_fpr: Decimal | None
