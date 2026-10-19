import pytest

from grocery_platform.retry import retry


class Flaky:
    """Fails a set number of times, then succeeds."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("boom")
        return "ok"


def test_returns_immediately_on_success() -> None:
    sleeps: list[float] = []
    func = Flaky(failures=0)
    assert retry(func, sleep=sleeps.append) == "ok"
    assert func.calls == 1
    assert sleeps == []


def test_retries_then_succeeds() -> None:
    sleeps: list[float] = []
    func = Flaky(failures=2)
    assert retry(func, attempts=4, sleep=sleeps.append) == "ok"
    assert func.calls == 3
    assert len(sleeps) == 2


def test_backoff_grows_exponentially() -> None:
    sleeps: list[float] = []
    func = Flaky(failures=3)
    retry(func, attempts=4, base_delay=1.0, sleep=sleeps.append)
    # Each delay is base * 2**n plus up to 50% jitter.
    for n, delay in enumerate(sleeps):
        assert 2**n <= delay <= 2**n * 1.5


def test_gives_up_after_max_attempts() -> None:
    sleeps: list[float] = []
    func = Flaky(failures=10)
    with pytest.raises(ConnectionError):
        retry(func, attempts=3, sleep=sleeps.append)
    assert func.calls == 3
    assert len(sleeps) == 2


def test_non_retryable_errors_fail_fast() -> None:
    sleeps: list[float] = []
    func = Flaky(failures=10)
    with pytest.raises(ConnectionError):
        retry(func, should_retry=lambda exc: False, sleep=sleeps.append)
    assert func.calls == 1
    assert sleeps == []


def test_attempts_must_be_positive() -> None:
    with pytest.raises(ValueError, match="attempts"):
        retry(lambda: None, attempts=0)
