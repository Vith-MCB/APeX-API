"""Instrumento vinculado a uma operação, sem reconhecimento prudencial."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Mitigator:
    row_id: str
    mitigator_id: str
    linked_operation_id: str
    guarantee_type: str
    guarantee_face_value: Decimal | None
