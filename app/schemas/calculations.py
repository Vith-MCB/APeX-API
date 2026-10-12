"""Contratos da validação individual, deliberadamente sem resultados prudenciais."""

from datetime import date
from typing import Literal

from pydantic import Field

from app.core.enums import CalculationMode
from app.schemas.common import IdentifierStr, StrictAPIModel, ValidationIssue
from app.schemas.context import CalculationContext
from app.schemas.mitigators import MitigatorInput
from app.schemas.operations import OperationInput


class ValidateExposureRequest(StrictAPIModel):
    context: CalculationContext
    operation: OperationInput
    mitigators: list[MitigatorInput] = Field(default_factory=list)


class ValidationReport(StrictAPIModel):
    exposure_id: IdentifierStr
    operation_id: IdentifierStr
    calculation_mode: CalculationMode
    reference_date: date
    mitigator_count: int
    issues: list[ValidationIssue]
    regulatory_calculation: Literal[False] = False


class ParquetLink(StrictAPIModel):
    operation_id: IdentifierStr
    exposure_id: IdentifierStr
    mitigator_ids: list[IdentifierStr]


class ParquetValidationReport(StrictAPIModel):
    operation_count: int
    exposure_count: int
    mitigator_count: int
    balance_total: str
    input_sha256: str
    links: list[ParquetLink]
    issues: list[ValidationIssue]
    regulatory_calculation: Literal[False] = False
