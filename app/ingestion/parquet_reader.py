"""Inspeção e leitura em batches de Parquet combined_v1."""

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from app.core.security import hash_file
from app.ingestion.schemas import get_arrow_schema

PARQUET_MAGIC = b"PAR1"


class ParquetReadError(Exception):
    """Arquivo recusado antes da normalização."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ParquetInfo:
    size_bytes: int
    sha256: str
    num_rows: int
    schema_version: str


def inspect_parquet(path: Path, *, max_bytes: int) -> ParquetInfo:
    size_bytes = path.stat().st_size
    if size_bytes > max_bytes:
        raise ParquetReadError("file exceeds the upload limit", status_code=413)
    with path.open("rb") as handle:
        if handle.read(4) != PARQUET_MAGIC:
            raise ParquetReadError("file is not a parquet file")

    try:
        parquet_file = pq.ParquetFile(path)
        _require_combined_schema(parquet_file.schema_arrow)
    except ParquetReadError:
        raise
    except (pa.ArrowException, OSError) as exc:
        raise ParquetReadError("file is not a readable parquet file") from exc

    return ParquetInfo(
        size_bytes=size_bytes,
        sha256=hash_file(path),
        num_rows=parquet_file.metadata.num_rows,
        schema_version="combined_v1",
    )


def iter_batches(path: Path, *, batch_size: int = 65_536):
    parquet_file = pq.ParquetFile(path)
    yield from parquet_file.iter_batches(batch_size=batch_size)


def _require_combined_schema(actual: pa.Schema) -> None:
    expected = get_arrow_schema("combined_v1")
    for field in expected:
        try:
            actual_field = actual.field(field.name)
        except KeyError as exc:
            raise ParquetReadError("parquet schema does not match combined_v1") from exc
        if not actual_field.type.equals(field.type):
            raise ParquetReadError("parquet schema does not match combined_v1")
