"""Sobe o worker local em um processo separado."""

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from app.worker.main import main as run_worker

    run_worker()


if __name__ == "__main__":
    main()
