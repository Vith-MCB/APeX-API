"""Decisão do FPR original, separada de RWA e capital."""

from dataclasses import dataclass
from decimal import Decimal

from app.core.enums import CalculationStatus
from app.schemas.common import ValidationIssue


@dataclass(frozen=True)
class OriginalFprDecision:
    status: CalculationStatus
    exposure_amount: Decimal | None
    original_fpr: Decimal | None
    rule_id: str
    article: str
    reasons: tuple[str, ...]
    issues: tuple[ValidationIssue, ...]
    didactic_not_regulatory: bool
    regulatory_calculation: bool = False
