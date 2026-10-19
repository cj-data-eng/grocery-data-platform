from pathlib import Path

import pyarrow.parquet as pq
import pytest

from grocery_platform.cli import main


def test_main_writes_a_partition(tmp_path: Path) -> None:
    exit_code = main(["--date", "2026-10-19", "--baskets", "10", "--out", str(tmp_path)])
    assert exit_code == 0
    files = list(tmp_path.rglob("*.parquet"))
    assert len(files) == 1
    assert pq.read_table(files[0]).num_rows > 0


def test_invalid_date_exits_with_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--date", "not-a-date", "--out", str(tmp_path)])
    assert excinfo.value.code == 2


def test_date_is_required() -> None:
    with pytest.raises(SystemExit):
        main([])