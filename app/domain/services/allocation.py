"""Parcela coberta e descoberta de um único mitigador elegível."""

from decimal import Decimal

from app.domain.rules.circ3809 import HAIRCUT


def recognized_value(market_value: Decimal) -> Decimal:
    """Aplica o haircut de 20% sobre o valor de mercado."""
    return market_value * HAIRCUT


def covered_and_uncovered(exposure_amount: Decimal, market_value: Decimal) -> tuple[Decimal, Decimal]:
    """Limita a parcela coberta ao menor valor entre E e o valor reconhecido."""
    covered = min(exposure_amount, recognized_value(market_value))
    return covered, exposure_amount - covered
