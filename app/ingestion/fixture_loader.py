"""Conversão de JSONL sintético para Parquet combined_v1."""

import json
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from app.core.money import parse_decimal
from app.ingestion.schemas import get_arrow_schema


def jsonl_to_parquet(source: Path, destination: Path) -> Path:
    records = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    write_combined_parquet(records, destination)
    return destination


def write_combined_parquet(records: list[dict], destination: Path) -> None:
    schema = get_arrow_schema("combined_v1")
    columns = []
    for field in schema:
        values = [_coerce(field, record.get(field.name)) for record in records]
        columns.append(pa.array(values, type=field.type))
    destination.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_arrays(columns, schema=schema), destination)


def _coerce(field: pa.Field, value: object) -> object:
    if value is None:
        return None
    if pa.types.is_decimal(field.type):
        if not isinstance(value, str):
            raise ValueError(f"{field.name} must be a decimal string")
        return parse_decimal(value)
    if pa.types.is_date(field.type):
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            raise ValueError(f"{field.name} must be an ISO date")
        return date.fromisoformat(value)
    return value
