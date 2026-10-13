"""Monta as duas parcelas quando há exatamente um título elegível."""

from app.core.enums import CalculationMode, CalculationStatus, TrancheType
from app.domain.models.decision import OriginalFprDecision
from app.domain.models.tranche import ExposureTranche
from app.domain.rules.bcb229 import ARTICLE as ORIGINAL_ARTICLE
from app.domain.rules.bcb229 import RULE_ID as ORIGINAL_RULE_ID
from app.domain.rules.circ3809 import (
    COVERED_FPR,
    RULE_ID,
    CollateralInput,
    SimpleApproachContextInput,
)
from app.domain.services.allocation import covered_and_uncovered
from app.domain.services.eligibility import assess_simple_federal_bond
from app.domain.services.reconciliation import tranches_sum_to_exposure


class MitigationDecision:
    def __init__(
        self,
        status: CalculationStatus | None,
        reasons: tuple[str, ...],
        tranches: tuple[ExposureTranche, ...],
        mitigator_ids: tuple[str, ...],
    ) -> None:
        self.status = status
        self.reasons = reasons
        self.tranches = tranches
        self.mitigator_ids = mitigator_ids


def resolve_simple_collateral(
    *,
    mode: CalculationMode,
    context: SimpleApproachContextInput,
    original: OriginalFprDecision,
    mitigators: tuple[CollateralInput, ...],
) -> MitigationDecision:
    """Publica parcelas só no modo didático e só para um mitigador elegível."""
    ids = tuple(item.mitigator_id for item in mitigators)
    if not mitigators:
        return MitigationDecision(None, (), (), ids)
    status, reasons = assess_simple_federal_bond(mitigators, context)
    if status is not CalculationStatus.CALCULATED:
        return MitigationDecision(status, reasons, (), ids)
    if original.exposure_amount is None or original.original_fpr is None:
        return MitigationDecision(CalculationStatus.INSUFFICIENT_DATA, ("missing_original_fpr",), (), ids)
    market_value = mitigators[0].market_value
    if market_value is None:
        return MitigationDecision(CalculationStatus.INSUFFICIENT_DATA, ("missing_market_value",), (), ids)
    covered, uncovered = covered_and_uncovered(original.exposure_amount, market_value)
    tranches = (
        ExposureTranche(TrancheType.COVERED_COLLATERAL_SIMPLE, covered, COVERED_FPR, RULE_ID, "6"),
        ExposureTranche(
            TrancheType.UNCOVERED,
            uncovered,
            original.original_fpr,
            ORIGINAL_RULE_ID,
            ORIGINAL_ARTICLE,
        ),
    )
    if not tranches_sum_to_exposure(original.exposure_amount, tranches):
        raise RuntimeError("covered and uncovered tranches do not sum to exposure")
    if mode is CalculationMode.DIDACTIC:
        return MitigationDecision(CalculationStatus.CALCULATED, reasons, tranches, ids)
    blocked = (
        "validation_only_does_not_calculate"
        if mode is CalculationMode.VALIDATION_ONLY
        else "regulatory_blocked_while_in_review"
    )
    return MitigationDecision(CalculationStatus.REQUIRES_REVIEW, reasons + (blocked,), (), ids)
