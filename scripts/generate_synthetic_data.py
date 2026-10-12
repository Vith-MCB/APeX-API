"""Gera Parquet somente com dados sintéticos."""

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.ingestion.fixture_loader import jsonl_to_parquet

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/combined_input.jsonl")
    destination = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/input/combined_v1.parquet")
    )
    print(jsonl_to_parquet(source, destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
