"""Write basket lines to Hive-partitioned Parquet files."""

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from grocery_platform.models import BasketLine

SCHEMA = pa.schema(
    [
        ("basket_id", pa.string()),
        ("store_id", pa.string()),
        ("customer_id", pa.string()),
        ("purchased_at", pa.timestamp("us", tz="UTC")),
        ("product_id", pa.string()),
        ("product_name", pa.string()),
        ("category", pa.string()),
        ("quantity", pa.int32()),
        ("unit_price_pence", pa.int32()),
    ]
)

DATASET_NAME = "basket_lines"


def lines_to_table(lines: Sequence[BasketLine]) -> pa.Table:
    """Convert lines to an Arrow table using the explicit schema."""
    columns = {name: [getattr(line, name) for line in lines] for name in SCHEMA.names}
    return pa.table(columns, schema=SCHEMA)


def partition_path(root: Path, day: date) -> Path:
    """Return the file path for a day's partition (Hive-style, Athena-friendly)."""
    return root / DATASET_NAME / f"purchase_date={day.isoformat()}" / "part-0000.parquet"


def write_partition(lines: Sequence[BasketLine], root: Path, day: date) -> Path:
    """Write one day's lines to Parquet and return the file path.

    Re-running for the same day overwrites that partition, so the load is idempotent.
    """
    if not lines:
        raise ValueError("no lines to write")
    path = partition_path(root, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(lines_to_table(lines), path, compression="snappy")
    return path