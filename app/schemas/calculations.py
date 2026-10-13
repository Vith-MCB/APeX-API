"""Contratos da validação individual, deliberadamente sem resultados prudenciais."""

from datetime import date
from typing import Literal

from pydantic import Field

from app.core.enums import CalculationMode, CalculationStatus, TrancheType
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


class TrancheReport(StrictAPIModel):
    tranche_type: TrancheType
    amount: str
    fpr: str
    rule_id: IdentifierStr
    article: str


class ExposureCalculationReport(StrictAPIModel):
    exposure_id: IdentifierStr
    operation_id: IdentifierStr
    calculation_mode: CalculationMode
    reference_date: date
    calculation_status: CalculationStatus
    rule_id: IdentifierStr
    article: str
    exposure_amount: str | None
    original_fpr: str | None
    reasons: list[str]
    issues: list[ValidationIssue]
    mitigator_ids: list[IdentifierStr] = Field(default_factory=list)
    mitigation_status: CalculationStatus | None = None
    mitigation_reasons: list[str] = Field(default_factory=list)
    tranches: list[TrancheReport] = Field(default_factory=list)
    didactic_not_regulatory: bool
    regulatory_calculation: Literal[False] = False


class ParquetValidationReport(StrictAPIModel):
    operation_count: int
    exposure_count: int
    mitigator_count: int
    balance_total: str
    input_sha256: str
    links: list[ParquetLink]
    issues: list[ValidationIssue]
    regulatory_calculation: Literal[False] = False
