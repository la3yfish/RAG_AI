from __future__ import annotations
import json
import sys
from typing import Any
from backend.core.interfaces import ILogSink

class StdoutJsonLogSink(ILogSink):
    def log_event(self, event: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
