"""E declarado pela instituição, nunca copiado do saldo contábil."""

from decimal import Decimal

from app.core.enums import CalculationStatus, ExposureValueBasis
from app.domain.rules.bcb229 import Art36Input


def declared_exposure_amount(
    data: Art36Input,
) -> tuple[CalculationStatus, Decimal | None, tuple[str, ...]]:
    """Aceita somente o valor já declarado nos arts. 5º e 6º."""
    if (
        data.exposure_value_basis is not ExposureValueBasis.INSTITUTION_DECLARED_ART5_ART6
        or data.provided_exposure_amount is None
    ):
        return (
            CalculationStatus.INSUFFICIENT_DATA,
            None,
            ("missing_declared_exposure_amount",),
        )
    if data.provided_exposure_amount < 0:
        return CalculationStatus.INVALID_INPUT, None, ("negative_exposure_amount",)
    return (
        CalculationStatus.CALCULATED,
        data.provided_exposure_amount,
        ("declared_exposure_amount",),
    )
