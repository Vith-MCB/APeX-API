"""Rastreio regulatório exportado, sem dado pessoal."""

from pathlib import Path

from app.reporting.exporter import write_traces
from app.reporting.portfolio import TraceExport


def export_trace(path: Path, rows: list[TraceExport]) -> None:
    write_traces(path, rows)
