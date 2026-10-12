"""Contratos Pydantic e Arrow do layout estrutural ``combined_v1``."""

from datetime import date
from typing import Annotated, Literal

import pyarrow as pa
from pydantic import Field

from app.core.enums import EligibilityEvidenceStatus, SchemaVersion
from app.schemas.common import IdentifierStr, MoneyStr, StrictAPIModel
from app.schemas.context import CurrencyCode


class CombinedOperationRecord(StrictAPIModel):
    record_type: Literal["OPERATION"]
    row_id: IdentifierStr
    operation_id: IdentifierStr
    granted_operation: None = None
    exposure_id: IdentifierStr
    mitigator_id: None = None
    reference_date: date
    product_type: IdentifierStr
    regulatory_exposure_class: IdentifierStr | None = None
    counterparty_id: IdentifierStr | None = None
    counterparty_type: IdentifierStr | None = None
    balance_amount: MoneyStr
    provided_exposure_amount: MoneyStr | None = None
    currency: CurrencyCode
    maturity_date: date | None = None
    is_off_balance: bool
    has_guarantee: bool
    guarantee_type: None = None
    collateral_subtype: None = None
    guarantee_face_value: None = None
    collateral_market_value: None = None
    guarantee_currency: None = None
    guarantee_maturity_date: None = None
    guarantor_type: None = None
    allocated_coverage_amount: None = None
    legal_enforceability_evidence: None = None
    eligibility_evidence_status: None = None
    source_system: IdentifierStr | None = None
    source_row_number: int | None = None
    cosif_account_code: IdentifierStr | None = None
    provided_fpr: MoneyStr | None = None


class CombinedGuaranteeRecord(StrictAPIModel):
    record_type: Literal["GUARANTEE"]
    row_id: IdentifierStr
    operation_id: None = None
    granted_operation: IdentifierStr
    exposure_id: IdentifierStr | None = None
    mitigator_id: IdentifierStr
    reference_date: date | None = None
    product_type: None = None
    regulatory_exposure_class: None = None
    counterparty_id: IdentifierStr | None = None
    counterparty_type: None = None
    balance_amount: None = None
    provided_exposure_amount: None = None
    currency: None = None
    maturity_date: None = None
    is_off_balance: None = None
    has_guarantee: None = None
    guarantee_type: IdentifierStr
    collateral_subtype: IdentifierStr | None = None
    guarantee_face_value: MoneyStr | None = None
    collateral_market_value: MoneyStr | None = None
    guarantee_currency: CurrencyCode | None = None
    guarantee_maturity_date: date | None = None
    guarantor_type: IdentifierStr | None = None
    allocated_coverage_amount: MoneyStr | None = None
    legal_enforceability_evidence: EligibilityEvidenceStatus | None = None
    eligibility_evidence_status: EligibilityEvidenceStatus | None = None
    source_system: IdentifierStr | None = None
    source_row_number: int | None = None
    cosif_account_code: IdentifierStr | None = None
    provided_fpr: None = None


CombinedRecord = Annotated[
    CombinedOperationRecord | CombinedGuaranteeRecord,
    Field(discriminator="record_type"),
]


def get_arrow_schema(schema_version: str | SchemaVersion) -> pa.Schema:
    """Retorna o schema físico sem atribuir significado regulatório aos campos."""
    try:
        version = SchemaVersion(schema_version)
    except ValueError as exc:
        raise ValueError(f"unsupported schema version: {schema_version}") from exc

    if version is not SchemaVersion.COMBINED_V1:  # pragma: no cover - future-proof guard
        raise ValueError(f"unsupported schema version: {schema_version}")

    money = pa.decimal128(38, 2)
    factor = pa.decimal128(38, 10)
    return pa.schema(
        [
            pa.field("record_type", pa.string(), nullable=False),
            pa.field("row_id", pa.string(), nullable=False),
            pa.field("operation_id", pa.string()),
            pa.field("granted_operation", pa.string()),
            pa.field("exposure_id", pa.string()),
            pa.field("mitigator_id", pa.string()),
            pa.field("reference_date", pa.date32()),
            pa.field("product_type", pa.string()),
            pa.field("regulatory_exposure_class", pa.string()),
            pa.field("counterparty_id", pa.string()),
            pa.field("counterparty_type", pa.string()),
            pa.field("balance_amount", money),
            pa.field("provided_exposure_amount", money),
            pa.field("currency", pa.string()),
            pa.field("maturity_date", pa.date32()),
            pa.field("is_off_balance", pa.bool_()),
            pa.field("has_guarantee", pa.bool_()),
            pa.field("guarantee_type", pa.string()),
            pa.field("collateral_subtype", pa.string()),
            pa.field("guarantee_face_value", money),
            pa.field("collateral_market_value", money),
            pa.field("guarantee_currency", pa.string()),
            pa.field("guarantee_maturity_date", pa.date32()),
            pa.field("guarantor_type", pa.string()),
            pa.field("allocated_coverage_amount", money),
            pa.field("legal_enforceability_evidence", pa.string()),
            pa.field("eligibility_evidence_status", pa.string()),
            pa.field("source_system", pa.string()),
            pa.field("source_row_number", pa.int64()),
            pa.field("cosif_account_code", pa.string()),
            pa.field("provided_fpr", factor),
        ]
    )
