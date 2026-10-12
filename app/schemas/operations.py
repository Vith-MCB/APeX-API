"""Contrato HTTP de uma operação submetida à validação."""

from datetime import date

from app.schemas.common import IdentifierStr, MoneyStr, StrictAPIModel
from app.schemas.context import CurrencyCode


class OperationInput(StrictAPIModel):
    operation_id: IdentifierStr
    exposure_id: IdentifierStr
    product_type: IdentifierStr
    balance_amount: MoneyStr
    currency: CurrencyCode
    has_guarantee: bool
    is_off_balance: bool
    regulatory_exposure_class: IdentifierStr | None = None
    counterparty_id: IdentifierStr | None = None
    counterparty_type: IdentifierStr | None = None
    provided_exposure_amount: MoneyStr | None = None
    maturity_date: date | None = None
    cosif_account_code: IdentifierStr | None = None
    provided_fpr: MoneyStr | None = None
