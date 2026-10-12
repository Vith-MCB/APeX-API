"""Entidades de origem já separadas do layout de arquivo."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Operation:
    row_id: str
    operation_id: str
    exposure_id: str
    reference_date: date
    product_type: str
    balance_amount: Decimal
    currency: str
    has_guarantee: bool
    is_off_balance: bool


@dataclass(frozen=True)
class Exposure:
    exposure_id: str
    operation_id: str
    source_row_id: str
