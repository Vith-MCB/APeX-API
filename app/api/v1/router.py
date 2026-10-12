"""Composição dos endpoints implementados da versão 1."""

from fastapi import APIRouter

from app.api.v1 import batches, health, validation


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(health.router)
    router.include_router(validation.router)
    router.include_router(batches.router)
    return router
