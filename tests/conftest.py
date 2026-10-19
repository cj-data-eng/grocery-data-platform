import pytest


@pytest.fixture(autouse=True)
def fake_aws_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure no test can ever talk to real AWS."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-2")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
