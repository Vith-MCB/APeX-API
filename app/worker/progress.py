"""Cancelamento cooperativo entre batches."""

from app.infrastructure.job_repository import JobRepository


class JobCancelled(Exception):
    """O lote foi cancelado antes da publicação."""


def check_cancel(repository: JobRepository, job_id: str) -> None:
    job = repository.get_job(job_id)
    if job is not None and job.cancel_requested:
        raise JobCancelled()
