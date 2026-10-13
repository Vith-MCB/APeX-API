"""Recorte da Abordagem Simples para um título público federal. A regra segue em revisão."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.enums import (
    AssociationScope,
    CollateralApproach,
    CollateralProviderType,
    EligibilityEvidenceStatus,
    MarketValueDatePolicy,
    MarkToMarketFrequency,
    MitigationRecognitionBarStatus,
    OverlapStatus,
    PrudentialScopeStatus,
    SimpleApproachUniformUseStatus,
)

RULE_ID = "CIRC3809_SIMPLE_TPF_BRL"
SUBTYPE = "FEDERAL_PUBLIC_BOND"
HAIRCUT = Decimal("0.80")
COVERED_FPR = Decimal("0")


@dataclass(frozen=True)
class CollateralInput:
    mitigator_id: str
    linked_operation_id: str
    guarantee_type: str | None
    collateral_subtype: str | None
    market_value: Decimal | None
    currency: str | None
    indexation_currency: str | None
    financial_indexer: str | None
    market_value_as_of: date | None
    mark_to_market_frequency: MarkToMarketFrequency | None
    market_value_date_policy: MarketValueDatePolicy | None
    mark_to_market_consistency_status: EligibilityEvidenceStatus | None
    effective_maturity_date: date | None
    overlap_status: OverlapStatus | None
    association_scope: AssociationScope | None
    institution_requirements_status: EligibilityEvidenceStatus | None
    provider_type: CollateralProviderType | None


@dataclass(frozen=True)
class SimpleApproachContextInput:
    reference_date: date
    operation_id: str
    approach: CollateralApproach
    prudential_scope_status: PrudentialScopeStatus | None
    fiscal_year_start: date | None
    fiscal_year_end: date | None
    election_date: date | None
    uniform_use_status: SimpleApproachUniformUseStatus | None
    recognition_bar_status: MitigationRecognitionBarStatus | None
    uses_sa_ccr: bool | None
    is_otc_derivative: bool | None
    exposure_currency: str
    exposure_indexation_currency: str | None
    exposure_financial_indexer: str | None
    exposure_maturity: date | None
