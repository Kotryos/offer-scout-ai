import io
import logging

from scout_coordinator.logging_context import configure_logging, correlation_id_scope


def test_configure_logging_adds_correlation_id_to_formatted_logs() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger()
    original_handlers = root.handlers[:]

    try:
        root.handlers = [handler]
        configure_logging("INFO")

        with correlation_id_scope("email-1"):
            logging.getLogger("test").info("Processed email")

        assert "[cid=email-1] Processed email" in stream.getvalue()
    finally:
        root.handlers = original_handlers


def test_configure_logging_keeps_http_client_request_logs_quiet() -> None:
    configure_logging("INFO")

    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
