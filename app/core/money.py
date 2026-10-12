"""Conversões monetárias estritas, sem política regulatória implícita."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN


def parse_decimal(value: str) -> Decimal:
    """Converte uma string decimal finita sem aceitar coerções numéricas."""
    if not isinstance(value, str):
        raise TypeError("decimal value must be provided as a string")

    if not value or value != value.strip():
        raise ValueError("decimal value must be a non-empty canonical string")

    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal value") from exc

    if not parsed.is_finite():
        raise ValueError("decimal value must be finite")
    return parsed


def quantize_money(
    value: Decimal,
    scale: int,
    *,
    rounding: str = ROUND_HALF_EVEN,
) -> Decimal:
    """Quantiza somente quando o chamador declara escala e arredondamento."""
    if not isinstance(value, Decimal):
        raise TypeError("value must be Decimal")
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0:
        raise ValueError("scale must be a non-negative integer")

    quantum = Decimal(1).scaleb(-scale)
    return value.quantize(quantum, rounding=rounding)
