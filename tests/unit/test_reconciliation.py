"""Conservação do valor e do RWA das parcelas."""

from decimal import Decimal

from app.core.enums import TrancheType
from app.domain.models.tranche import ExposureTranche
from app.domain.services.reconciliation import (
    tranche_rwa_sums_to_total,
    tranches_sum_to_exposure,
)
from app.domain.services.rwa import calculate_rwa


def test_tranches_conserve_exposure_and_mitigated_rwa() -> None:
    tranches = (
        ExposureTranche(
            TrancheType.COVERED_COLLATERAL_SIMPLE,
            Decimal("80000.00"),
            Decimal("0"),
            "CIRC3809_SIMPLE_TPF_BRL",
            "6",
        ),
        ExposureTranche(
            TrancheType.UNCOVERED,
            Decimal("45000.00"),
            Decimal("0.85"),
            "BCB229_ART36_PJ_NAO_FINANCEIRA",
            "36",
        ),
    )
    result = calculate_rwa(Decimal("125000.00"), Decimal("0.85"), tranches)

    assert tranches_sum_to_exposure(Decimal("125000.00"), tranches)
    assert tranche_rwa_sums_to_total(
        result.tranche_contributions,
        result.after_mitigation,
    )
    assert result.after_mitigation == Decimal("38250.0000")
