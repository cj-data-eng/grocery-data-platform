"""Send custom events to New Relic.

Observability must never break the pipeline: every failure here is logged and swallowed.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections.abc import Mapping

from grocery_platform.retry import retry

logger = logging.getLogger(__name__)

EVENT_ENDPOINTS = {
    "us": "https://insights-collector.newrelic.com/v1/accounts/{account_id}/events",
    "eu": "https://insights-collector.eu01.nr-data.net/v1/accounts/{account_id}/events",
}


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _is_transient(exc: Exception) -> bool:
    """Retry rate limiting, server errors and network problems, but not bad requests or keys."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, urllib.error.URLError | TimeoutError)


def send_event(
    event_type: str,
    attributes: Mapping[str, object],
    *,
    attempts: int = 3,
    timeout: float = 5.0,
) -> bool:
    """Send one custom event. Returns True if New Relic accepted it, False otherwise.

    Does nothing (and returns False) unless NEW_RELIC_LICENSE_KEY and NEW_RELIC_ACCOUNT_ID
    are set, so local runs and tests stay quiet.
    """
    license_key = os.environ.get("NEW_RELIC_LICENSE_KEY")
    account_id = os.environ.get("NEW_RELIC_ACCOUNT_ID")
    if not license_key or not account_id:
        return False

    region = os.environ.get("NEW_RELIC_REGION", "us").lower()
    if region not in EVENT_ENDPOINTS:
        logger.warning("unknown New Relic region", extra={"region": region})
        return False

    payload = json.dumps([{"eventType": event_type, **attributes}], default=str).encode()
    request = urllib.request.Request(
        EVENT_ENDPOINTS[region].format(account_id=account_id),
        data=payload,
        headers={"Api-Key": license_key, "Content-Type": "application/json"},
        method="POST",
    )

    def post() -> None:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()

    try:
        retry(post, attempts=attempts, base_delay=0.5, should_retry=_is_transient, sleep=_sleep)
    except (urllib.error.URLError, TimeoutError) as exc:
        # Log what went wrong, but never the request itself: it carries the license key.
        logger.warning(
            "could not send event to New Relic",
            extra={"event_type": event_type, "error": type(exc).__name__, "detail": str(exc)},
        )
        return False
    return True
