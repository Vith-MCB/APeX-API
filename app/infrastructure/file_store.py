"""Arquivos de job confinados a data/ e publicação atômica."""

import shutil
from pathlib import Path
from uuid import UUID

from app.core.security import hash_file
from app.ingestion.parquet_reader import ParquetReadError

AREAS = frozenset({"input", "work", "output"})
UPLOAD_NAME = "upload.parquet"


class UnsafePath(Exception):
    """Caminho recusado por sair do diretório de dados."""


class FileStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def save_upload(self, source, job_id: str, *, max_bytes: int) -> tuple[Path, str]:
        directory = job_directory(self.data_dir, "input", job_id)
        directory.mkdir(parents=True, exist_ok=False)
        destination = directory / UPLOAD_NAME
        if hasattr(source, "seek"):
            source.seek(0)
        size = 0
        with destination.open("wb") as handle:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    handle.close()
                    shutil.rmtree(directory, ignore_errors=True)
                    raise ParquetReadError("file exceeds the upload limit", status_code=413)
                handle.write(chunk)
            handle.flush()
        return destination, hash_file(destination)

    def input_file(self, job_id: str) -> Path:
        return job_directory(self.data_dir, "input", job_id) / UPLOAD_NAME

    def work_directory(self, job_id: str) -> Path:
        directory = job_directory(self.data_dir, "work", job_id)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def output_directory(self, job_id: str) -> Path:
        return job_directory(self.data_dir, "output", job_id)

    def artifact_path(self, job_id: str, filename: str) -> Path:
        directory = self.output_directory(job_id)
        candidate = (directory / filename).resolve()
        if not candidate.is_relative_to(directory.resolve()):
            raise UnsafePath("artifact path escapes the job output")
        return candidate

    def publish(self, job_id: str) -> Path:
        source = job_directory(self.data_dir, "work", job_id)
        destination = self.output_directory(job_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise UnsafePath("job output already exists")
        source.replace(destination)
        return destination

    def discard_work(self, job_id: str) -> None:
        directory = job_directory(self.data_dir, "work", job_id)
        shutil.rmtree(directory, ignore_errors=True)

    def discard_input(self, job_id: str) -> None:
        directory = job_directory(self.data_dir, "input", job_id)
        shutil.rmtree(directory, ignore_errors=True)

    def discard_output(self, job_id: str) -> None:
        directory = job_directory(self.data_dir, "output", job_id)
        shutil.rmtree(directory, ignore_errors=True)

    def is_published(self, job_id: str) -> bool:
        return self.artifact_path(job_id, "manifest.json").is_file()


def job_directory(data_dir: Path, area: str, job_id: str) -> Path:
    if area not in AREAS:
        raise UnsafePath("storage area is not allowed")
    try:
        parsed = UUID(job_id)
    except ValueError as exc:
        raise UnsafePath("job id is not valid") from exc
    if str(parsed) != job_id:
        raise UnsafePath("job id is not canonical")
    root = data_dir.resolve()
    candidate = (root / area / job_id).resolve()
    if not candidate.is_relative_to(root):
        raise UnsafePath("path escapes the data directory")
    return candidate
