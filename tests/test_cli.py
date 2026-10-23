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


def test_main_reports_a_success_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        "grocery_platform.cli.send_event", lambda name, attrs: sent.append((name, dict(attrs)))
    )
    monkeypatch.setenv("RUN_SOURCE", "test-suite")

    assert main(["--date", "2026-10-19", "--baskets", "10", "--out", str(tmp_path)]) == 0

    assert len(sent) == 1
    name, event = sent[0]
    assert name == "GroceryPipelineRun"
    assert event["status"] == "success"
    assert event["partition_date"] == "2026-10-19"
    assert event["run_source"] == "test-suite"
    assert isinstance(event["row_count"], int) and event["row_count"] > 0
    assert "duration_s" in event


@mock_aws
def test_main_reports_a_failed_event_when_upload_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, object]] = []
    monkeypatch.setattr(
        "grocery_platform.cli.send_event", lambda name, attrs: sent.append(dict(attrs))
    )

    exit_code = main(
        ["--date", "2026-10-19", "--baskets", "10", "--out", str(tmp_path), "--bucket", "nope"]
    )

    assert exit_code == 1
    assert sent[0]["status"] == "failed"
    assert sent[0]["uploaded"] is True


def test_main_reports_a_failed_event_when_the_run_crashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, object]] = []
    monkeypatch.setattr(
        "grocery_platform.cli.send_event", lambda name, attrs: sent.append(dict(attrs))
    )

    def explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("grocery_platform.cli.write_partition", explode)

    with pytest.raises(RuntimeError):
        main(["--date", "2026-10-19", "--baskets", "10", "--out", str(tmp_path)])
    assert sent[0]["status"] == "failed"
