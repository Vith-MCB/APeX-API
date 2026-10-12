"""SQLite local em WAL para metadados de jobs."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    calculation_mode TEXT NOT NULL,
    reference_date TEXT NOT NULL,
    context_json TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    heartbeat_at TEXT,
    worker_id TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    total_rows INTEGER,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    operation_count INTEGER,
    exposure_count INTEGER,
    mitigator_count INTEGER,
    issue_count INTEGER NOT NULL DEFAULT 0,
    balance_total TEXT,
    error_message TEXT
)
"""


def connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize_db(database: Path) -> None:
    with connect(database) as connection:
        connection.execute(SCHEMA)
