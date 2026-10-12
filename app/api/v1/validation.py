"""Validação estrutural individual e de Parquet, sem execução de regras prudenciais."""

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, UploadFile
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.enums import IssueCode
from app.core.errors import PublicAPIError
from app.core.money import quantize_money
from app.ingestion.combined_normalizer import normalize_combined, operation_balance_total
from app.ingestion.parquet_reader import ParquetReadError, inspect_parquet
from app.ingestion.relationship_validator import validate_links
from app.schemas.calculations import (
    ParquetLink,
    ParquetValidationReport,
    ValidateExposureRequest,
    ValidationReport,
)
from app.schemas.common import ErrorResponse, ValidationIssue
from app.schemas.context import CalculationContext

router = APIRouter(prefix="/validate", tags=["validation"])


@router.post(
    "/exposure",
    response_model=ValidationReport,
    responses={422: {"model": ErrorResponse}},
)
def validate_exposure(request: ValidateExposureRequest) -> ValidationReport:
    issues: list[ValidationIssue] = []
    operation = request.operation

    if operation.has_guarantee != bool(request.mitigators):
        issues.append(
            ValidationIssue(
                code=IssueCode.FLAG_RELATION_MISMATCH,
                field="operation.has_guarantee",
                message="has_guarantee is inconsistent with the submitted mitigators",
            )
        )

    for index, mitigator in enumerate(request.mitigators):
        if mitigator.linked_operation_id != operation.operation_id:
            issues.append(
                ValidationIssue(
                    code=IssueCode.ORPHAN_GUARANTEE,
                    field=f"mitigators.{index}.linked_operation_id",
                    message="linked_operation_id does not match operation.operation_id",
                )
            )

    return ValidationReport(
        exposure_id=operation.exposure_id,
        operation_id=operation.operation_id,
        calculation_mode=request.context.calculation_mode,
        reference_date=request.context.reference_date,
        mitigator_count=len(request.mitigators),
        issues=issues,
    )


@router.post(
    "/parquet",
    response_model=ParquetValidationReport,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def validate_parquet(
    file: UploadFile,
    context: Annotated[str, Form()],
) -> ParquetValidationReport:
    try:
        parsed_context = CalculationContext.model_validate_json(context)
    except ValidationError as exc:
        raise PublicAPIError(
            "INVALID_SCHEMA",
            "context does not match the calculation contract",
            status_code=422,
            details=[
                {
                    "loc": [
                        part
                        for part in error.get("loc", ())
                        if isinstance(part, str | int)
                    ],
                    "message": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ],
        ) from exc

    temporary_path: Path | None = None
    try:
        temporary_path = _write_upload(file, max_bytes=get_settings().max_upload_bytes)
        parquet_info = inspect_parquet(
            temporary_path,
            max_bytes=get_settings().max_upload_bytes,
        )
        if parsed_context.schema_version.value != parquet_info.schema_version:
            raise ParquetReadError("context schema_version does not match the file")
        canonical = validate_links(normalize_combined(temporary_path))
    except ParquetReadError as exc:
        raise PublicAPIError(
            "INVALID_SCHEMA",
            exc.message,
            status_code=exc.status_code,
        ) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    balance_total = quantize_money(operation_balance_total(canonical.operations), 2)
    links = [
        ParquetLink(
            operation_id=operation.operation_id,
            exposure_id=operation.exposure_id,
            mitigator_ids=[
                mitigator.mitigator_id
                for mitigator in canonical.mitigators
                if mitigator.linked_operation_id == operation.operation_id
            ],
        )
        for operation in canonical.operations
    ]
    return ParquetValidationReport(
        operation_count=len(canonical.operations),
        exposure_count=len(canonical.exposures),
        mitigator_count=len(canonical.mitigators),
        balance_total=f"{balance_total:.2f}",
        input_sha256=parquet_info.sha256,
        links=links,
        issues=canonical.issues,
    )


def _write_upload(upload: UploadFile, *, max_bytes: int) -> Path:
    with tempfile.NamedTemporaryFile(delete=False) as temporary:
        size = 0
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                Path(temporary.name).unlink(missing_ok=True)
                raise ParquetReadError("file exceeds the upload limit", status_code=413)
            temporary.write(chunk)
        return Path(temporary.name)

