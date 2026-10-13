"""RWA do subconjunto didático suportado."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.models.tranche import ExposureTranche


@dataclass(frozen=True)
class RwaResult:
    before_mitigation: Decimal
    after_mitigation: Decimal
    delta: Decimal
    tranche_contributions: tuple[Decimal, ...]


def calculate_baseline_rwa(exposure_amount: Decimal, original_fpr: Decimal) -> Decimal:
    """Calcula o RWA da exposição sem reconhecer mitigação."""
    return exposure_amount * original_fpr


def calculate_mitigated_rwa(tranches: tuple[ExposureTranche, ...]) -> Decimal:
    """Soma o RWA de parcelas já consideradas elegíveis."""
    return sum((tranche.amount * tranche.fpr for tranche in tranches), Decimal("0"))


def calculate_rwa(
    exposure_amount: Decimal,
    original_fpr: Decimal,
    tranches: tuple[ExposureTranche, ...] = (),
) -> RwaResult:
    """Compara o RWA original com o resultado das parcelas, quando presentes."""
    before = calculate_baseline_rwa(exposure_amount, original_fpr)
    contributions = tuple(tranche.amount * tranche.fpr for tranche in tranches)
    after = sum(contributions, Decimal("0")) if tranches else before
    return RwaResult(
        before_mitigation=before,
        after_mitigation=after,
        delta=before - after,
        tranche_contributions=contributions,
    )
