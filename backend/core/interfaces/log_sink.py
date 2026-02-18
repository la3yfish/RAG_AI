from __future__ import annotations

from typing import Any, Protocol


class ILogSink(Protocol):
    """Replaceable event logger (stdout/json/file/otel)."""

    def log_event(self, event: dict[str, Any]) -> None:
        ...
