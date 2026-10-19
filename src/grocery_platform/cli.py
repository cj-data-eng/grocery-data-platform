"""Command line entry point."""

import argparse
import logging
import time
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import boto3
from botocore.config import Config

from grocery_platform.generator import generate_baskets
from grocery_platform.logging_config import configure_logging
from grocery_platform.uploader import UploadError, upload_file
from grocery_platform.validation import split_valid
from grocery_platform.writer import write_partition

logger = logging.getLogger("grocery_platform")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grocery-platform",
        description="Generate synthetic grocery baskets, write Parquet, optionally upload to S3.",
    )
    parser.add_argument("--date", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    parser.add_argument("--baskets", type=int, default=1000, help="number of baskets")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data"), help="output directory")
    parser.add_argument("--bucket", help="S3 bucket to upload to (skip to keep files local)")
    parser.add_argument("--region", default="eu-west-2")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()
    started = time.monotonic()

    lines = list(generate_baskets(args.date, args.baskets, seed=args.seed))
    valid, rejected = split_valid(lines)
    if rejected:
        logger.warning("rejected lines", extra={"rejected": len(rejected)})

    path = write_partition(valid, args.out, args.date)
    logger.info(
        "wrote partition",
        extra={"rows": len(valid), "baskets": args.baskets, "path": str(path)},
    )

    if args.bucket:
        key = path.relative_to(args.out).as_posix()
        # We do our own retrying, so switch off botocore's to avoid retrying twice.
        client = boto3.client(
            "s3", region_name=args.region, config=Config(retries={"max_attempts": 1})
        )
        try:
            size = upload_file(client, path, args.bucket, key)
        except UploadError:
            logger.exception("upload failed", extra={"bucket": args.bucket, "s3_key": key})
            return 1
        logger.info(
            "uploaded partition", extra={"bucket": args.bucket, "s3_key": key, "bytes": size}
        )

    logger.info("run complete", extra={"duration_s": round(time.monotonic() - started, 2)})
    return 0
