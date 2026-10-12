"""Metadados públicos da versão 1 da API."""

from typing import Literal

from fastapi import APIRouter

from app.core.enums import CalculationMode
from app.schemas.common import StrictAPIModel

router = APIRouter(tags=["service"])


class ServiceInfo(StrictAPIModel):
    service: str
    version: str
    supported_modes: list[CalculationMode]
    offline: Literal[True]


@router.get("/info", response_model=ServiceInfo)
def service_info() -> ServiceInfo:
    return ServiceInfo(
        service="APeX-API",
        version="0.1.0",
        supported_modes=list(CalculationMode),
        offline=True,
    )
