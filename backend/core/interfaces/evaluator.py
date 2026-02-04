from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EvalResult:
    ok: bool
    stage_name: str
    metrics: dict[str, Any]
    details: dict[str, Any]  # per-case info; keep small in MVP


class IEvaluator(Protocol):
    """Evaluation + staged tests runner abstraction."""

    def run_golden(self, *, golden_path: str) -> EvalResult:
        ...

    def run_stage(self, *, stage_name: str) -> EvalResult:
        ...
