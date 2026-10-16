"""Explicit, idempotent CLI: python -m rippleproof.seed."""

import logging

from rippleproof.config import Settings
from rippleproof.errors import DatabaseUnavailable, GraphQueryError
from rippleproof.repository import GraphRepository
from rippleproof.seed_data import build_dataset


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        summary = GraphRepository(Settings()).seed(build_dataset())
    except (DatabaseUnavailable, GraphQueryError):
        logging.exception("Seed failed; no fallback data was used. Fix FalkorDB, then rerun.")
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
