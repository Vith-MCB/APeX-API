"""Contexto declarado para validação e cálculos futuros."""

from datetime import date
from typing import Annotated

from pydantic import StringConstraints

from app.core.enums import CalculationMode, CollateralApproach, MinimumPrScope, SchemaVersion
from app.schemas.common import IdentifierStr, StrictAPIModel

CurrencyCode = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{3}$")]


class CalculationContext(StrictAPIModel):
    schema_version: SchemaVersion = SchemaVersion.COMBINED_V1
    reference_date: date
    institution_profile: IdentifierStr
    capital_regime: IdentifierStr
    collateral_approach: CollateralApproach
    rule_set_version: IdentifierStr
    calculation_mode: CalculationMode
    reporting_currency: CurrencyCode = "BRL"
    strict_mode: bool = True
    minimum_pr_scope: MinimumPrScope | None = None
