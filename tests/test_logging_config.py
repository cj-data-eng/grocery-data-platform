import json
import logging
import sys

from grocery_platform.logging_config import JsonFormatter, configure_logging


def make_record(**extra: object) -> logging.LogRecord:
    logger = logging.getLogger("test")
    record = logger.makeRecord("test", logging.INFO, "f.py", 1, "hello %s", ("world",), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_output_is_valid_json_with_core_fields() -> None:
    payload = json.loads(JsonFormatter().format(make_record()))
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert "time" in payload


def test_extra_fields_are_included() -> None:
    payload = json.loads(JsonFormatter().format(make_record(rows=42, bucket="b")))
    assert payload["rows"] == 42
    assert payload["bucket"] == "b"


def test_exception_is_captured() -> None:
    try:
        raise ValueError("bad")
    except ValueError:
        record = make_record()
        record.exc_info = sys.exc_info()
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: bad" in payload["exception"]


def test_configure_logging_is_idempotent() -> None:
    configure_logging()
    configure_logging()
    root = logging.getLogger()
    ours = [h for h in root.handlers if getattr(h, "_grocery_platform_json", False)]
    assert len(ours) == 1
