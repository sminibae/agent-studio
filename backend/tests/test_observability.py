import json
import logging

from agent_studio.platform.observability import JsonLogFormatter


def test_json_log_includes_available_correlation_fields() -> None:
    record = logging.LogRecord(
        name="agent_studio.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="request complete",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.owner_id = "owner-456"

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "request complete"
    assert payload["request_id"] == "request-123"
    assert payload["owner_id"] == "owner-456"
