"""Testes das conversões decimais sem pressupor regra regulatória."""

from decimal import Decimal

import pytest

from app.core.money import parse_decimal, quantize_money


@pytest.mark.parametrize("value", ["0", "0.00"])
def test_zero_is_a_decimal_value(value):
    assert parse_decimal(value) == Decimal("0")


def test_none_does_not_become_zero():
    with pytest.raises(TypeError):
        parse_decimal(None)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", ""])
def test_non_finite_or_empty_values_are_rejected(value):
    with pytest.raises(ValueError):
        parse_decimal(value)


def test_numeric_input_is_not_coerced():
    with pytest.raises(TypeError):
        parse_decimal(1.5)


def test_quantization_requires_an_explicit_scale():
    assert quantize_money(Decimal("0.005"), 2) == Decimal("0.00")


@pytest.mark.parametrize("scale", [-1, 1.5, True])
def test_invalid_scale_is_rejected(scale):
    with pytest.raises(ValueError):
        quantize_money(Decimal("1"), scale)
