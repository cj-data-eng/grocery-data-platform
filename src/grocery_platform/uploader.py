"""Upload files to S3, retrying transient failures only."""

from pathlib import Path
from typing import Any

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from grocery_platform.retry import retry

TRANSIENT_ERROR_CODES = frozenset(
    {"SlowDown", "InternalError", "ServiceUnavailable", "RequestTimeout", "Throttling"}
)
TRANSIENT_NETWORK_ERRORS = (
    ConnectTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
    ReadTimeoutError,
)


class UploadError(RuntimeError):
    """Raised when a file could not be uploaded."""


def is_transient(exc: Exception) -> bool:
    """True for errors worth retrying (throttling, 5xx, network blips).

    Permanent errors such as AccessDenied or NoSuchBucket are not transient: retrying
    them only wastes time and hides the real problem.
    """
    if isinstance(exc, TRANSIENT_NETWORK_ERRORS):
        return True
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        return code in TRANSIENT_ERROR_CODES or status >= 500
    return False


def upload_file(client: Any, path: Path, bucket: str, key: str) -> int:
    """Upload ``path`` to ``s3://bucket/key`` and return the number of bytes sent."""
    body = path.read_bytes()

    def put() -> None:
        client.put_object(Bucket=bucket, Key=key, Body=body, ServerSideEncryption="AES256")

    try:
        retry(put, should_retry=is_transient)
    except (BotoCoreError, ClientError) as exc:
        raise UploadError(f"failed to upload {path} to s3://{bucket}/{key}: {exc}") from exc
    return len(body)
