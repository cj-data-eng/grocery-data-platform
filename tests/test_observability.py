import json
import logging
import urllib.error
import urllib.request
from typing import Any

import pytest

from grocery_platform.observability import send_event

SECRET = "super-secret-license-key"


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"success":true}'


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEW_RELIC_LICENSE_KEY", SECRET)
    monkeypatch.setenv("NEW_RELIC_ACCOUNT_ID", "12345")
    monkeypatch.delenv("NEW_RELIC_REGION", raising=False)
    monkeypatch.setattr("time.sleep", lambda seconds: None)


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://example.com", code, "err", {}, None)  # type: ignore[arg-type]


def test_does_nothing_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEW_RELIC_LICENSE_KEY", raising=False)
    monkeypatch.delenv("NEW_RELIC_ACCOUNT_ID", raising=False)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("must not call the network")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    assert send_event("Thing", {"a": 1}) is False


@pytest.mark.usefixtures("configured")
def test_sends_event_to_us_endpoint_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        seen.append(request)
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert send_event("GroceryPipelineRun", {"status": "success", "row_count": 5}) is True

    request = seen[0]
    assert request.full_url == "https://insights-collector.newrelic.com/v1/accounts/12345/events"
    assert request.get_header("Api-key") == SECRET
    assert request.get_header("Content-type") == "application/json"
    assert request.data is not None
    assert json.loads(request.data) == [
        {"eventType": "GroceryPipelineRun", "status": "success", "row_count": 5}
    ]


@pytest.mark.usefixtures("configured")
def test_eu_region_uses_eu_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEW_RELIC_REGION", "EU")
    seen: list[str] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        seen.append(request.full_url)
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert send_event("X", {}) is True
    assert seen == ["https://insights-collector.eu01.nr-data.net/v1/accounts/12345/events"]


@pytest.mark.usefixtures("configured")
def test_unknown_region_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEW_RELIC_REGION", "mars")
    assert send_event("X", {}) is False


@pytest.mark.usefixtures("configured")
def test_transient_errors_are_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def flaky(request: urllib.request.Request, timeout: float) -> FakeResponse:
        calls.append(1)
        if len(calls) < 3:
            raise http_error(503)
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", flaky)
    assert send_event("X", {}) is True
    assert len(calls) == 3


@pytest.mark.usefixtures("configured")
def test_bad_key_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def forbidden(request: urllib.request.Request, timeout: float) -> FakeResponse:
        calls.append(1)
        raise http_error(403)

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    assert send_event("X", {}) is False
    assert len(calls) == 1


@pytest.mark.usefixtures("configured")
def test_network_failure_never_raises_and_never_logs_the_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def down(request: urllib.request.Request, timeout: float) -> FakeResponse:
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    with caplog.at_level(logging.WARNING):
        assert send_event("X", {}, attempts=2) is False

    assert "could not send event" in caplog.text
    assert SECRET not in caplog.text
