"""Parcelas coberta e descoberta de uma exposição."""

from dataclasses import dataclass
from decimal import Decimal

from app.core.enums import TrancheType


@dataclass(frozen=True)
class ExposureTranche:
    tranche_type: TrancheType
    amount: Decimal
    fpr: Decimal
    rule_id: str
    article: str
