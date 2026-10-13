"""Elegibilidade estrita de um título público federal na Abordagem Simples."""

from app.core.enums import (
    AssociationScope,
    CalculationStatus,
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
from app.domain.rules.circ3809 import (
    SUBTYPE,
    CollateralInput,
    SimpleApproachContextInput,
)

Check = tuple[CalculationStatus, str]


def assess_simple_federal_bond(
    mitigators: tuple[CollateralInput, ...],
    context: SimpleApproachContextInput,
) -> tuple[CalculationStatus, tuple[str, ...]]:
    """Confere todas as guardas antes de permitir o FPR coberto igual a zero."""
    context_checks = (
        _prudential_scope(context),
        _simple_approach(context),
        _excluded_routes(context),
        _recognition_bar(context),
    )
    for status, reason in context_checks:
        if status is not CalculationStatus.CALCULATED:
            return status, (reason,)

    if len(mitigators) != 1:
        return CalculationStatus.UNSUPPORTED, ("multiple_mitigators_not_in_cut",)
    collateral = mitigators[0]
    collateral_checks = (
        _link(collateral, context.operation_id),
        _instrument(collateral),
        _provider(collateral),
        _overlap(collateral),
        _association(collateral),
        _requirements(collateral),
        _currency_and_indexation(collateral, context),
        _market_value(collateral),
        _daily_mark(collateral, context),
        _maturity(collateral, context),
    )
    for status, reason in collateral_checks:
        if status is not CalculationStatus.CALCULATED:
            return status, (reason,)
    return CalculationStatus.CALCULATED, ("simple_federal_bond_eligible",)


def _prudential_scope(context: SimpleApproachContextInput) -> Check:
    status = context.prudential_scope_status
    if status is None or status is PrudentialScopeStatus.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_prudential_scope"
    if status is not PrudentialScopeStatus.RWA_CPAD:
        return CalculationStatus.UNSUPPORTED, "prudential_scope_out_of_cut"
    return CalculationStatus.CALCULATED, "rwa_cpad_scope"


def _simple_approach(context: SimpleApproachContextInput) -> Check:
    if context.approach is not CollateralApproach.SIMPLE:
        return CalculationStatus.UNSUPPORTED, "collateral_approach_out_of_cut"
    if (
        context.fiscal_year_start is None
        or context.fiscal_year_end is None
        or context.election_date is None
    ):
        return CalculationStatus.INSUFFICIENT_DATA, "missing_simple_approach_dates"
    if context.fiscal_year_start > context.fiscal_year_end:
        return CalculationStatus.INVALID_INPUT, "invalid_fiscal_year_period"
    if not context.fiscal_year_start <= context.reference_date <= context.fiscal_year_end:
        return CalculationStatus.REQUIRES_REVIEW, "reference_date_outside_fiscal_year"
    if not context.fiscal_year_start <= context.election_date <= context.fiscal_year_end:
        return CalculationStatus.REQUIRES_REVIEW, "simple_approach_election_outside_fiscal_year"
    uniform = context.uniform_use_status
    if uniform is None or uniform is SimpleApproachUniformUseStatus.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_simple_approach_uniform_use"
    if uniform is SimpleApproachUniformUseStatus.NOT_UNIFORM:
        return CalculationStatus.UNSUPPORTED, "simple_approach_not_used_uniformly"
    return CalculationStatus.CALCULATED, "simple_approach_declared"


def _excluded_routes(context: SimpleApproachContextInput) -> Check:
    if context.uses_sa_ccr is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_sa_ccr_declaration"
    if context.uses_sa_ccr:
        return CalculationStatus.UNSUPPORTED, "sa_ccr_out_of_cut"
    if context.is_otc_derivative is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_otc_derivative_declaration"
    if context.is_otc_derivative:
        return CalculationStatus.UNSUPPORTED, "article_7_otc_derivative_out_of_cut"
    return CalculationStatus.CALCULATED, "excluded_routes_absent"


def _recognition_bar(context: SimpleApproachContextInput) -> Check:
    status = context.recognition_bar_status
    if status is None or status is MitigationRecognitionBarStatus.UNKNOWN:
        return CalculationStatus.REQUIRES_REVIEW, "unknown_mitigation_recognition_bar"
    if status is MitigationRecognitionBarStatus.BARRED:
        return CalculationStatus.NOT_APPLICABLE, "mitigation_recognition_barred"
    return CalculationStatus.CALCULATED, "recognition_not_barred"


def _link(collateral: CollateralInput, operation_id: str) -> Check:
    if collateral.linked_operation_id != operation_id:
        return CalculationStatus.UNSUPPORTED, "mitigator_not_linked_to_operation"
    return CalculationStatus.CALCULATED, "linked"


def _instrument(collateral: CollateralInput) -> Check:
    if collateral.guarantee_type is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_guarantee_type"
    if collateral.guarantee_type != "COLLATERAL":
        return CalculationStatus.UNSUPPORTED, "guarantee_type_out_of_cut"
    if collateral.collateral_subtype is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_collateral_subtype"
    if collateral.collateral_subtype != SUBTYPE:
        return CalculationStatus.UNSUPPORTED, "collateral_subtype_out_of_cut"
    return CalculationStatus.CALCULATED, "federal_public_bond_collateral"


def _provider(collateral: CollateralInput) -> Check:
    provider = collateral.provider_type
    if provider is None or provider is CollateralProviderType.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_collateral_provider"
    if provider is CollateralProviderType.OTHER:
        return CalculationStatus.UNSUPPORTED, "collateral_provider_out_of_cut"
    return CalculationStatus.CALCULATED, "collateral_provider_supported"


def _overlap(collateral: CollateralInput) -> Check:
    if collateral.overlap_status is None or collateral.overlap_status is OverlapStatus.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_overlap_declaration"
    if collateral.overlap_status is OverlapStatus.PRESENT:
        return CalculationStatus.REQUIRES_REVIEW, "collateral_overlap"
    return CalculationStatus.CALCULATED, "no_overlap"


def _association(collateral: CollateralInput) -> Check:
    scope = collateral.association_scope
    if scope is None or scope is AssociationScope.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_association_scope"
    if scope is AssociationScope.MULTIPLE_EXPOSURES:
        return CalculationStatus.UNSUPPORTED, "shared_collateral_not_in_cut"
    return CalculationStatus.CALCULATED, "unique_exposure"


def _requirements(collateral: CollateralInput) -> Check:
    status = collateral.institution_requirements_status
    if status is None or status is EligibilityEvidenceStatus.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_institution_requirements"
    if status is EligibilityEvidenceStatus.NOT_MET:
        return CalculationStatus.NOT_APPLICABLE, "institution_requirements_not_met"
    if status is EligibilityEvidenceStatus.VERIFIED:
        return CalculationStatus.REQUIRES_REVIEW, "verification_is_not_an_apex_audit"
    return CalculationStatus.CALCULATED, "requirements_declared"


def _currency_and_indexation(
    collateral: CollateralInput,
    context: SimpleApproachContextInput,
) -> Check:
    if collateral.currency is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_collateral_currency"
    if collateral.currency != context.exposure_currency:
        return CalculationStatus.UNSUPPORTED, "currency_mismatch"
    if (
        collateral.indexation_currency is None
        or context.exposure_indexation_currency is None
    ):
        return CalculationStatus.INSUFFICIENT_DATA, "missing_indexation_currency"
    if collateral.indexation_currency != context.exposure_indexation_currency:
        return CalculationStatus.UNSUPPORTED, "indexation_currency_mismatch"
    if collateral.financial_indexer is None or context.exposure_financial_indexer is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_financial_indexer"
    if collateral.financial_indexer != context.exposure_financial_indexer:
        return CalculationStatus.UNSUPPORTED, "financial_indexer_mismatch"
    return CalculationStatus.CALCULATED, "currency_and_indexation_match"


def _market_value(collateral: CollateralInput) -> Check:
    if collateral.market_value is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_market_value"
    if collateral.market_value <= 0:
        return CalculationStatus.NOT_APPLICABLE, "market_value_not_positive"
    return CalculationStatus.CALCULATED, "market_value"


def _daily_mark(
    collateral: CollateralInput,
    context: SimpleApproachContextInput,
) -> Check:
    consistency = collateral.mark_to_market_consistency_status
    if consistency is None or consistency is EligibilityEvidenceStatus.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_mark_consistency_declaration"
    if consistency is EligibilityEvidenceStatus.NOT_MET:
        return CalculationStatus.NOT_APPLICABLE, "market_value_not_consistent"
    if consistency is EligibilityEvidenceStatus.VERIFIED:
        return CalculationStatus.REQUIRES_REVIEW, "verification_is_not_an_apex_audit"
    if collateral.mark_to_market_frequency is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_mark_frequency"
    if collateral.mark_to_market_frequency is not MarkToMarketFrequency.DAILY:
        return CalculationStatus.NOT_APPLICABLE, "mark_to_market_not_daily"
    if collateral.market_value_as_of is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_market_value_date"
    if collateral.market_value_as_of > context.reference_date:
        return CalculationStatus.INVALID_INPUT, "market_value_after_reference_date"
    policy = collateral.market_value_date_policy
    if policy is None or policy is MarketValueDatePolicy.UNKNOWN:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_market_value_date_policy"
    if (
        policy is MarketValueDatePolicy.REFERENCE_DATE
        and collateral.market_value_as_of != context.reference_date
    ):
        return CalculationStatus.REQUIRES_REVIEW, "market_value_not_on_reference_date"
    if (
        policy is MarketValueDatePolicy.PREVIOUS_BUSINESS_DAY_DECLARED
        and collateral.market_value_as_of >= context.reference_date
    ):
        return CalculationStatus.REQUIRES_REVIEW, "invalid_previous_business_day_declaration"
    return CalculationStatus.CALCULATED, "daily_mark_valid_for_reference_date"


def _maturity(
    collateral: CollateralInput,
    context: SimpleApproachContextInput,
) -> Check:
    if collateral.effective_maturity_date is None or context.exposure_maturity is None:
        return CalculationStatus.INSUFFICIENT_DATA, "missing_effective_maturity"
    if collateral.effective_maturity_date < context.exposure_maturity:
        return CalculationStatus.NOT_APPLICABLE, "collateral_matures_before_exposure"
    return CalculationStatus.CALCULATED, "maturity"
