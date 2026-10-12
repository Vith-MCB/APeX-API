"""Tratamento central de erros HTTP sem stack trace ou conteúdo financeiro."""

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import PublicAPIError
from app.schemas.common import ErrorResponse


def _correlation_id(request: Request) -> str:
    supplied = request.headers.get("X-Correlation-ID")
    return supplied.strip() if supplied and supplied.strip() else str(uuid4())


async def request_validation_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    correlation_id = _correlation_id(request)
    details = [
        {
            "loc": list(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    body = ErrorResponse(
        code="INVALID_SCHEMA",
        message="Request validation failed",
        details=details,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=422,
        content=body.model_dump(mode="json"),
        headers={"X-Correlation-ID": correlation_id},
    )


async def public_api_error_handler(request: Request, exc: PublicAPIError) -> JSONResponse:
    correlation_id = _correlation_id(request)
    body = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(mode="json"),
        headers={"X-Correlation-ID": correlation_id},
    )


def register_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(PublicAPIError, public_api_error_handler)
