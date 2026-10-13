"""FPR original do art. 36. O modo regulatório permanece sem número."""

from decimal import Decimal

from app.core.enums import CalculationMode, CalculationStatus, IssueCode
from app.domain.models.decision import OriginalFprDecision
from app.domain.rules.bcb229 import ARTICLE, ORIGINAL_FPR, RULE_ID, Art36Input
from app.domain.services.classification import classify_article_36
from app.domain.services.exposure_builder import declared_exposure_amount
from app.schemas.common import ValidationIssue


def resolve_original_fpr(data: Art36Input, mode: CalculationMode) -> OriginalFprDecision:
    """Calcula o candidato e só publica o número no modo didático."""
    status, reasons = classify_article_36(data)
    issues = _provided_fpr_issue(data.provided_fpr)
    if status is not CalculationStatus.CALCULATED:
        return _without_numbers(status, reasons, issues)

    amount_status, amount, amount_reasons = declared_exposure_amount(data)
    if amount_status is not CalculationStatus.CALCULATED:
        return _without_numbers(amount_status, amount_reasons, issues)

    if mode is CalculationMode.DIDACTIC:
        return OriginalFprDecision(
            status=CalculationStatus.CALCULATED,
            exposure_amount=amount,
            original_fpr=ORIGINAL_FPR,
            rule_id=RULE_ID,
            article=ARTICLE,
            reasons=reasons + amount_reasons,
            issues=issues,
            didactic_not_regulatory=True,
        )
    blocked = (
        "validation_only_does_not_calculate"
        if mode is CalculationMode.VALIDATION_ONLY
        else "regulatory_blocked_while_in_review"
    )
    return _without_numbers(CalculationStatus.REQUIRES_REVIEW, reasons + (blocked,), issues)


def _without_numbers(
    status: CalculationStatus,
    reasons: tuple[str, ...],
    issues: tuple[ValidationIssue, ...],
) -> OriginalFprDecision:
    return OriginalFprDecision(
        status=status,
        exposure_amount=None,
        original_fpr=None,
        rule_id=RULE_ID,
        article=ARTICLE,
        reasons=reasons,
        issues=issues,
        didactic_not_regulatory=False,
    )


def _provided_fpr_issue(provided_fpr: Decimal | None) -> tuple[ValidationIssue, ...]:
    if provided_fpr is None:
        return ()
    return (
        ValidationIssue(
            code=IssueCode.PROVIDED_FPR_IGNORED,
            field="operation.provided_fpr",
            message="provided_fpr is diagnostic and is not the applied factor",
        ),
    )
