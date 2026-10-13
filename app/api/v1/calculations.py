"""Cálculo individual do FPR original. O modo regulatório permanece bloqueado."""

from decimal import Decimal

from fastapi import APIRouter

from app.core.enums import CalculationMode, CalculationStatus
from app.core.money import parse_decimal, quantize_money
from app.domain.models.decision import OriginalFprDecision
from app.domain.rules.bcb229 import Art36Input
from app.domain.rules.circ3809 import (
    HAIRCUT,
    RULE_ID as COLLATERAL_RULE_ID,
    CollateralInput,
    SimpleApproachContextInput,
)
from app.domain.services.capital import MinimumPrDecision, calculate_minimum_pr_contribution
from app.domain.services.exposure_links import validate_exposure_links
from app.domain.services.fpr import resolve_original_fpr
from app.domain.services.reconciliation import tranche_rwa_sums_to_total
from app.domain.services.rwa import RwaResult, calculate_baseline_rwa, calculate_rwa
from app.domain.services.tranche_builder import MitigationDecision, resolve_simple_collateral
from app.schemas.calculations import (
    AppliedRuleReport,
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
    relationship_issues = validate_exposure_links(
        operation_id=request.operation.operation_id,
        has_guarantee=request.operation.has_guarantee,
        linked_operation_ids=tuple(
            item.linked_operation_id for item in request.mitigators
        ),
    )
    mitigators = tuple(_collateral_input(item) for item in request.mitigators)
    if relationship_issues:
        mitigation = MitigationDecision(
            CalculationStatus.INVALID_INPUT,
            ("invalid_exposure_mitigator_links",),
            (),
            tuple(item.mitigator_id for item in mitigators),
        )
    else:
        mitigation = resolve_simple_collateral(
            mode=request.context.calculation_mode,
            context=_simple_approach_context(request),
            original=candidate,
            mitigators=mitigators,
        )
    publish = mitigation.status is CalculationStatus.CALCULATED
    publish_post_mitigation = mitigation.status in {
        None,
        CalculationStatus.CALCULATED,
        CalculationStatus.NOT_APPLICABLE,
    }
    baseline_rwa: Decimal | None = None
    rwa: RwaResult | None = None
    minimum_pr: MinimumPrDecision | None = None
    if (
        request.context.calculation_mode is CalculationMode.DIDACTIC
        and candidate.exposure_amount is not None
        and candidate.original_fpr is not None
    ):
        baseline_rwa = calculate_baseline_rwa(
            candidate.exposure_amount,
            candidate.original_fpr,
        )
        if publish_post_mitigation:
            applied_tranches = mitigation.tranches if publish else ()
            rwa = calculate_rwa(
                candidate.exposure_amount,
                candidate.original_fpr,
                applied_tranches,
            )
            if applied_tranches and not tranche_rwa_sums_to_total(
                rwa.tranche_contributions,
                rwa.after_mitigation,
            ):
                raise RuntimeError("tranche RWA does not sum to mitigated RWA")
            minimum_pr = calculate_minimum_pr_contribution(
                rwa.after_mitigation,
                request.context.minimum_pr_scope,
            )
    tranches = [
        TrancheReport(
            tranche_type=tranche.tranche_type,
            amount=_money_text(tranche.amount) or "0.00",
            fpr=format(tranche.fpr, "f"),
            rwa_contribution=_money_text(rwa.tranche_contributions[index]) or "0.00",
            rule_id=tranche.rule_id,
            article=tranche.article,
        )
        for index, tranche in enumerate(mitigation.tranches)
    ]
    applied_rules = (
        _applied_rules(candidate, publish, minimum_pr)
        if baseline_rwa is not None
        else []
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
        issues=list(decision.issues) + list(relationship_issues),
        mitigator_ids=list(mitigation.mitigator_ids),
        mitigation_status=mitigation.status,
        mitigation_reasons=list(mitigation.reasons),
        tranches=tranches if publish else [],
        rwa_before_mitigation=_money_text(baseline_rwa),
        rwa_after_mitigation=_money_text(rwa.after_mitigation) if rwa else None,
        rwa_delta=_money_text(rwa.delta) if rwa else None,
        minimum_pr_contribution=(
            _money_text(minimum_pr.contribution) if minimum_pr else None
        ),
        minimum_pr_status=minimum_pr.status if minimum_pr else None,
        minimum_pr_reasons=list(minimum_pr.reasons) if minimum_pr else [],
        applied_rules=applied_rules,
        didactic_not_regulatory=decision.didactic_not_regulatory,
    )


def _applied_rules(
    original: OriginalFprDecision,
    mitigation_applied: bool,
    minimum_pr: MinimumPrDecision | None,
) -> list[AppliedRuleReport]:
    if original.original_fpr is None:
        return []
    rules = [
        AppliedRuleReport(
            rule_id=original.rule_id,
            article=original.article,
            factor=format(original.original_fpr, "f"),
        )
    ]
    if mitigation_applied:
        rules.extend(
            (
                AppliedRuleReport(
                    rule_id=COLLATERAL_RULE_ID,
                    article="6, § 1º",
                    factor=format(HAIRCUT, "f"),
                ),
                AppliedRuleReport(
                    rule_id=COLLATERAL_RULE_ID,
                    article="6, I",
                    factor="0",
                ),
            )
        )
    if minimum_pr is not None and minimum_pr.contribution is not None:
        rules.append(
            AppliedRuleReport(
                rule_id=minimum_pr.rule_id,
                article=minimum_pr.article,
                factor=format(minimum_pr.factor, "f"),
            )
        )
    return rules


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


def _simple_approach_context(
    request: ValidateExposureRequest,
) -> SimpleApproachContextInput:
    context = request.context
    operation = request.operation
    return SimpleApproachContextInput(
        reference_date=context.reference_date,
        operation_id=operation.operation_id,
        approach=context.collateral_approach,
        prudential_scope_status=context.prudential_scope_status,
        fiscal_year_start=context.fiscal_year_start,
        fiscal_year_end=context.fiscal_year_end,
        election_date=context.simple_approach_election_date,
        uniform_use_status=context.simple_approach_uniform_use_status,
        recognition_bar_status=context.mitigation_recognition_bar_status,
        uses_sa_ccr=context.uses_sa_ccr,
        is_otc_derivative=operation.is_otc_derivative,
        exposure_currency=operation.currency,
        exposure_indexation_currency=operation.exposure_indexation_currency,
        exposure_financial_indexer=operation.exposure_financial_indexer,
        exposure_maturity=operation.exposure_effective_maturity_date,
    )


def _collateral_input(item: MitigatorInput) -> CollateralInput:
    return CollateralInput(
        mitigator_id=item.mitigator_id,
        linked_operation_id=item.linked_operation_id,
        guarantee_type=item.guarantee_type,
        collateral_subtype=item.collateral_subtype,
        market_value=_optional_decimal(item.collateral_market_value),
        currency=item.guarantee_currency,
        indexation_currency=item.collateral_indexation_currency,
        financial_indexer=item.collateral_financial_indexer,
        market_value_as_of=item.market_value_as_of,
        mark_to_market_frequency=item.mark_to_market_frequency,
        market_value_date_policy=item.market_value_date_policy,
        mark_to_market_consistency_status=item.mark_to_market_consistency_status,
        effective_maturity_date=item.collateral_effective_maturity_date,
        overlap_status=item.overlap_status,
        association_scope=item.association_scope,
        institution_requirements_status=item.institution_requirements_status,
        provider_type=item.collateral_provider_type,
    )


def _optional_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return parse_decimal(value)


def _money_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(quantize_money(value, 2), "f")
