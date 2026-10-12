"""Processo local que consome a fila persistida."""

import time

from app.worker.job_runner import run_once


def main() -> None:
    while True:
        if not run_once():
            time.sleep(0.5)


if __name__ == "__main__":
    main()
