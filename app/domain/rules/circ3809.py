"""Recorte da Abordagem Simples para um título público federal. A regra segue em revisão."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.enums import AssociationScope, EligibilityEvidenceStatus, MarkToMarketFrequency, OverlapStatus

RULE_ID = "CIRC3809_SIMPLE_TPF_BRL"
SUBTYPE = "FEDERAL_PUBLIC_BOND"
HAIRCUT = Decimal("0.80")
COVERED_FPR = Decimal("0")


@dataclass(frozen=True)
class CollateralInput:
    mitigator_id: str
    linked_operation_id: str
    collateral_subtype: str | None
    market_value: Decimal | None
    currency: str | None
    collateral_indexer: str | None
    market_value_as_of: date | None
    mark_to_market_frequency: MarkToMarketFrequency | None
    effective_maturity_date: date | None
    overlap_status: OverlapStatus | None
    association_scope: AssociationScope | None
    institution_requirements_status: EligibilityEvidenceStatus | None
