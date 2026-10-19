"""Command line entry point."""

import argparse
import logging
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from grocery_platform.generator import generate_baskets
from grocery_platform.validation import split_valid
from grocery_platform.writer import write_partition

logger = logging.getLogger("grocery_platform")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grocery-platform",
        description="Generate synthetic grocery baskets and write them as Parquet.",
    )
    parser.add_argument("--date", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    parser.add_argument("--baskets", type=int, default=1000, help="number of baskets")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data"), help="output directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    lines = list(generate_baskets(args.date, args.baskets, seed=args.seed))
    valid, rejected = split_valid(lines)
    if rejected:
        logger.warning("rejected %d lines", len(rejected))

    path = write_partition(valid, args.out, args.date)
    logger.info("wrote %d lines to %s", len(valid), path)
    return 0
