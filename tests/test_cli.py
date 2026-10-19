from pathlib import Path

import boto3
import pyarrow.parquet as pq
import pytest
from moto import mock_aws

from grocery_platform.cli import main

BUCKET = "test-raw-bucket"
KEY = "basket_lines/purchase_date=2026-10-19/part-0000.parquet"


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


@mock_aws
def test_main_uploads_to_s3_when_bucket_given(tmp_path: Path) -> None:
    client = boto3.client("s3", region_name="eu-west-2")
    client.create_bucket(
        Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
    )

    exit_code = main(
        ["--date", "2026-10-19", "--baskets", "10", "--out", str(tmp_path), "--bucket", BUCKET]
    )

    assert exit_code == 0
    keys = [o["Key"] for o in client.list_objects_v2(Bucket=BUCKET)["Contents"]]
    assert keys == [KEY]


@mock_aws
def test_main_returns_1_when_upload_fails(tmp_path: Path) -> None:
    exit_code = main(
        ["--date", "2026-10-19", "--baskets", "10", "--out", str(tmp_path), "--bucket", "nope"]
    )
    assert exit_code == 1
