"""Confere se as parcelas somam a exposição declarada."""

from decimal import Decimal

from app.domain.models.tranche import ExposureTranche


def tranches_sum_to_exposure(exposure_amount: Decimal, tranches: tuple[ExposureTranche, ...]) -> bool:
    return sum((tranche.amount for tranche in tranches), Decimal("0")) == exposure_amount


def tranche_rwa_sums_to_total(
    tranche_rwa: tuple[Decimal, ...],
    total_rwa: Decimal,
) -> bool:
    return sum(tranche_rwa, Decimal("0")) == total_rwa
