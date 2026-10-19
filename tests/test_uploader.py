from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from moto import mock_aws

from grocery_platform.uploader import UploadError, is_transient, upload_file

BUCKET = "test-raw-bucket"
KEY = "basket_lines/purchase_date=2026-10-19/part-0000.parquet"


def client_error(code: str, status: int) -> ClientError:
    response: Any = {
        "Error": {"Code": code, "Message": "x"},
        "ResponseMetadata": {"HTTPStatusCode": status},
    }
    return ClientError(response, "PutObject")


def test_throttling_and_server_errors_are_transient() -> None:
    assert is_transient(client_error("SlowDown", 503))
    assert is_transient(client_error("SomethingOdd", 500))


def test_permission_and_missing_bucket_errors_are_permanent() -> None:
    assert not is_transient(client_error("AccessDenied", 403))
    assert not is_transient(client_error("NoSuchBucket", 404))


def test_network_errors_are_transient() -> None:
    assert is_transient(EndpointConnectionError(endpoint_url="https://s3.example.com"))


def test_unrelated_errors_are_not_transient() -> None:
    assert not is_transient(ValueError("nope"))


@mock_aws
def test_upload_puts_encrypted_object(tmp_path: Path) -> None:
    client = boto3.client("s3", region_name="eu-west-2")
    client.create_bucket(
        Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
    )
    file = tmp_path / "part-0000.parquet"
    file.write_bytes(b"hello parquet")

    size = upload_file(client, file, BUCKET, KEY)

    assert size == len(b"hello parquet")
    obj = client.get_object(Bucket=BUCKET, Key=KEY)
    assert obj["Body"].read() == b"hello parquet"
    assert obj["ServerSideEncryption"] == "AES256"


@mock_aws
def test_missing_bucket_raises_upload_error_without_retrying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", sleeps.append)
    client = boto3.client("s3", region_name="eu-west-2")
    file = tmp_path / "f.parquet"
    file.write_bytes(b"x")

    with pytest.raises(UploadError, match="NoSuchBucket"):
        upload_file(client, file, "bucket-that-does-not-exist", "k")
    assert sleeps == []
