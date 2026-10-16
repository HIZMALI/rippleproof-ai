"""Add missing inbound fixtures without restoring/replacing base seed values."""

import logging

from rippleproof.config import Settings
from rippleproof.errors import DatabaseUnavailable, GraphQueryError
from rippleproof.inbound_data import build_inbound_extension
from rippleproof.repository import GraphRepository


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        summary = GraphRepository(Settings()).migrate_inbound(build_inbound_extension())
    except (DatabaseUnavailable, GraphQueryError):
        logging.exception("Additive inbound migration failed; existing data was not reset")
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
