"""Elegibilidade de um único título público federal na Abordagem Simples."""

from datetime import date

from app.core.enums import (
    AssociationScope,
    CalculationStatus,
    EligibilityEvidenceStatus,
    MarkToMarketFrequency,
    OverlapStatus,
)
from app.domain.rules.circ3809 import SUBTYPE, CollateralInput


def assess_simple_federal_bond(
    mitigators: tuple[CollateralInput, ...],
    *,
    operation_id: str,
    currency: str,
    exposure_indexer: str | None,
    exposure_maturity: date | None,
    reference_date: date,
) -> tuple[CalculationStatus, tuple[str, ...]]:
    """Confere as condições deste recorte. Não divide exposição entre garantias."""
    if len(mitigators) != 1:
        return CalculationStatus.UNSUPPORTED, ("multiple_mitigators_not_in_cut",)
    collateral = mitigators[0]
    checks = (
        _link(collateral, operation_id),
        _subtype(collateral),
        _overlap(collateral),
        _association(collateral),
        _requirements(collateral),
        _currency(collateral, currency),
        _indexer(collateral, exposure_indexer),
        _market_value(collateral),
        _daily_mark(collateral, reference_date),
        _maturity(collateral, exposure_maturity),
    )
    for status, reason in checks:
        if status is not CalculationStatus.CALCULATED:
            return status, (reason,)
    return CalculationStatus.CALCULATED, ("simple_federal_bond_eligible",)


def _link(collateral: CollateralInput, operation_id: str) -> tuple[CalculationStatus, str]:
    if collateral.linked_operation_id != operation_id:
        return CalculationStatus.UNSUPPORTED, "mitigator_not_linked_to_operation"
    return CalculationStatus.CALCULATED, "linked"


def _subtype(collateral: CollateralInput) -> tuple[CalculationStatus, str]:
    if collateral.collateral_subtype is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_collateral_subtype"
    if collateral.collateral_subtype != SUBTYPE:
        return CalculationStatus.UNSUPPORTED, "collateral_subtype_out_of_cut"
    return CalculationStatus.CALCULATED, "subtype"


def _overlap(collateral: CollateralInput) -> tuple[CalculationStatus, str]:
    if collateral.overlap_status is None or collateral.overlap_status is OverlapStatus.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_overlap_declaration"
    if collateral.overlap_status is OverlapStatus.PRESENT:
        return CalculationStatus.REQUIRES_REVIEW, "collateral_overlap"
    return CalculationStatus.CALCULATED, "no_overlap"


def _association(collateral: CollateralInput) -> tuple[CalculationStatus, str]:
    scope = collateral.association_scope
    if scope is None or scope is AssociationScope.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_association_scope"
    if scope is AssociationScope.MULTIPLE_EXPOSURES:
        return CalculationStatus.UNSUPPORTED, "shared_collateral_not_in_cut"
    return CalculationStatus.CALCULATED, "unique_exposure"


def _requirements(collateral: CollateralInput) -> tuple[CalculationStatus, str]:
    status = collateral.institution_requirements_status
    if status is None or status is EligibilityEvidenceStatus.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_institution_requirements"
    if status is EligibilityEvidenceStatus.NOT_MET:
        return CalculationStatus.NOT_APPLICABLE, "institution_requirements_not_met"
    if status is EligibilityEvidenceStatus.VERIFIED:
        return CalculationStatus.REQUIRES_REVIEW, "verification_is_not_an_apex_audit"
    return CalculationStatus.CALCULATED, "requirements_declared"


def _currency(collateral: CollateralInput, currency: str) -> tuple[CalculationStatus, str]:
    if collateral.currency is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_collateral_currency"
    if collateral.currency != currency:
        return CalculationStatus.UNSUPPORTED, "currency_mismatch"
    return CalculationStatus.CALCULATED, "currency"


def _indexer(
    collateral: CollateralInput,
    exposure_indexer: str | None,
) -> tuple[CalculationStatus, str]:
    if collateral.collateral_indexer is None and exposure_indexer is None:
        return CalculationStatus.CALCULATED, "no_indexer"
    if collateral.collateral_indexer is None or exposure_indexer is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_indexer"
    if collateral.collateral_indexer != exposure_indexer:
        return CalculationStatus.UNSUPPORTED, "indexer_mismatch"
    return CalculationStatus.CALCULATED, "indexer"


def _market_value(collateral: CollateralInput) -> tuple[CalculationStatus, str]:
    if collateral.market_value is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_market_value"
    if collateral.market_value <= 0:
        return CalculationStatus.NOT_APPLICABLE, "market_value_not_positive"
    return CalculationStatus.CALCULATED, "market_value"


def _daily_mark(
    collateral: CollateralInput,
    reference_date: date,
) -> tuple[CalculationStatus, str]:
    if collateral.mark_to_market_frequency is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_mark_frequency"
    if collateral.mark_to_market_frequency is not MarkToMarketFrequency.DAILY:
        return CalculationStatus.NOT_APPLICABLE, "mark_to_market_not_daily"
    if collateral.market_value_as_of is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_market_value_date"
    if collateral.market_value_as_of > reference_date:
        return CalculationStatus.INVALID_INPUT, "market_value_after_reference_date"
    return CalculationStatus.CALCULATED, "daily_mark"


def _maturity(
    collateral: CollateralInput,
    exposure_maturity: date | None,
) -> tuple[CalculationStatus, str]:
    if collateral.effective_maturity_date is None or exposure_maturity is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_effective_maturity"
    if collateral.effective_maturity_date < exposure_maturity:
        return CalculationStatus.NOT_APPLICABLE, "collateral_matures_before_exposure"
    return CalculationStatus.CALCULATED, "maturity"
