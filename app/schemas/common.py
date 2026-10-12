"""Tipos compartilhados pelos contratos HTTP."""

from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.core.money import parse_decimal


def _validate_identifier(value: str) -> str:
    if not value.strip():
        raise ValueError("identifier must not be empty")
    if value != value.strip():
        raise ValueError("identifier must not have surrounding whitespace")
    return value


def _validate_money_string(value: str) -> str:
    parsed = parse_decimal(value)
    if parsed < 0:
        raise ValueError("amount must be non-negative")
    return value


IdentifierStr = Annotated[
    str,
    StringConstraints(strict=True, min_length=1),
    AfterValidator(_validate_identifier),
]
MoneyStr = Annotated[
    str,
    StringConstraints(strict=True, min_length=1),
    AfterValidator(_validate_money_string),
]


class StrictAPIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(StrictAPIModel):
    loc: list[str | int]
    message: str
    type: str


class ErrorResponse(StrictAPIModel):
    code: str
    message: str
    details: list[ErrorDetail | dict[str, Any]]
    correlation_id: str


class ValidationIssue(StrictAPIModel):
    code: str
    field: str
    message: str
