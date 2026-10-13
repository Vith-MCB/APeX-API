"""Contrato HTTP estrutural de mitigadores, sem decisão de elegibilidade."""

from datetime import date

from app.core.enums import AssociationScope, EligibilityEvidenceStatus, MarkToMarketFrequency, OverlapStatus
from app.schemas.common import IdentifierStr, MoneyStr, StrictAPIModel
from app.schemas.context import CurrencyCode


class MitigatorInput(StrictAPIModel):
    mitigator_id: IdentifierStr
    linked_operation_id: IdentifierStr
    guarantee_type: IdentifierStr
    collateral_subtype: IdentifierStr | None = None
    guarantee_face_value: MoneyStr | None = None
    collateral_market_value: MoneyStr | None = None
    guarantee_currency: CurrencyCode | None = None
    guarantee_maturity_date: date | None = None
    guarantor_type: IdentifierStr | None = None
    allocated_coverage_amount: MoneyStr | None = None
    legal_enforceability_evidence: EligibilityEvidenceStatus | None = None
    eligibility_evidence_status: EligibilityEvidenceStatus | None = None
    collateral_indexer: IdentifierStr | None = None
    market_value_as_of: date | None = None
    mark_to_market_frequency: MarkToMarketFrequency | None = None
    collateral_effective_maturity_date: date | None = None
    overlap_status: OverlapStatus | None = None
    association_scope: AssociationScope | None = None
    institution_requirements_status: EligibilityEvidenceStatus | None = None
