import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return _correlation_id.get()


@contextmanager
def correlation_id_scope(correlation_id: str) -> Iterator[None]:
    token = _correlation_id.set(correlation_id)
    try:
        yield
    finally:
        _correlation_id.reset(token)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    if not root.handlers:
        root.addHandler(logging.StreamHandler())

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)5s --- [%(threadName)s] %(name)s : [cid=%(correlation_id)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    for handler in root.handlers:
        handler.setFormatter(formatter)
        handler.addFilter(CorrelationIdFilter())
