"""Contribuição isolada do subconjunto calculado ao requerimento mínimo de PR."""

from dataclasses import dataclass
from decimal import Decimal

from app.core.enums import CalculationStatus, MinimumPrScope
from app.domain.rules.cmn4958 import ARTICLE, MINIMUM_PR_FACTOR, RULE_ID


@dataclass(frozen=True)
class MinimumPrDecision:
    status: CalculationStatus
    contribution: Decimal | None
    rule_id: str
    article: str
    factor: Decimal | None
    reasons: tuple[str, ...]


def calculate_minimum_pr_contribution(
    rwa: Decimal,
    scope: MinimumPrScope | None,
) -> MinimumPrDecision:
    """Aplica 8% somente quando a instituição declara estar no âmbito do art. 1º."""
    if scope is None or scope is MinimumPrScope.UNKNOWN:
        return _without_number(CalculationStatus.INSUFFICIENT_DATA, "missing_minimum_pr_scope")
    if scope is MinimumPrScope.ARTICLE_1_EXCLUDED:
        return _without_number(CalculationStatus.NOT_APPLICABLE, "institution_excluded_by_article_1")
    if scope is MinimumPrScope.SEGMENT_5:
        return _without_number(CalculationStatus.NOT_APPLICABLE, "segment_5_out_of_scope")
    if scope is MinimumPrScope.CREDIT_COOPERATIVE_ART7:
        return _without_number(CalculationStatus.UNSUPPORTED, "article_7_addition_not_implemented")
    return MinimumPrDecision(
        status=CalculationStatus.CALCULATED,
        contribution=rwa * MINIMUM_PR_FACTOR,
        rule_id=RULE_ID,
        article=ARTICLE,
        factor=MINIMUM_PR_FACTOR,
        reasons=("article_4_factor_applied_to_calculated_subset",),
    )


def _without_number(status: CalculationStatus, reason: str) -> MinimumPrDecision:
    return MinimumPrDecision(
        status=status,
        contribution=None,
        rule_id=RULE_ID,
        article=ARTICLE,
        factor=None,
        reasons=(reason,),
    )
