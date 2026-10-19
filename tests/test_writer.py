from datetime import date
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from grocery_platform.generator import generate_baskets
from grocery_platform.writer import SCHEMA, partition_path, write_partition

DAY = date(2026, 10, 19)


def test_writes_hive_partitioned_file(tmp_path: Path) -> None:
    lines = list(generate_baskets(DAY, 20))
    path = write_partition(lines, tmp_path, DAY)
    assert path == tmp_path / "basket_lines" / "purchase_date=2026-10-19" / "part-0000.parquet"
    assert path.exists()


def test_round_trip_preserves_rows_and_schema(tmp_path: Path) -> None:
    lines = list(generate_baskets(DAY, 20))
    path = write_partition(lines, tmp_path, DAY)
    table = pq.read_table(path)
    assert table.num_rows == len(lines)
    assert table.schema.equals(SCHEMA)
    assert table.column("basket_id").to_pylist() == [line.basket_id for line in lines]


def test_rerun_overwrites_instead_of_duplicating(tmp_path: Path) -> None:
    lines = list(generate_baskets(DAY, 20))
    write_partition(lines, tmp_path, DAY)
    path = write_partition(lines, tmp_path, DAY)
    assert pq.read_table(path).num_rows == len(lines)
    assert len(list(path.parent.iterdir())) == 1


def test_empty_input_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no lines"):
        write_partition([], tmp_path, DAY)


def test_partition_path_is_pure(tmp_path: Path) -> None:
    assert partition_path(tmp_path, DAY).parent.name == "purchase_date=2026-10-19"
