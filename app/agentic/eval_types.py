"""Eval Types module helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Sequence


@dataclass(frozen=True)
class EvalResult:
    passed: bool
    score: float
    diff_json: Dict[str, Any]
    metrics_json: Dict[str, Any]


class AgentEvaluator(Protocol):
    def validate_expected(self, expected_json: Dict[str, Any]) -> None:
        """Validate expected."""
        # Fail fast on bad input.
        ...

    def evaluate(
        self,
        expected_json: Dict[str, Any],
        actual_json: Optional[Dict[str, Any]],
        *,
        agent_status: str,
    ) -> EvalResult:
        """Handle the value."""
        # Keep the main step clear.
        ...

    def aggregate(self, results: Sequence[EvalResult]) -> Dict[str, Any]:
        """Handle the value."""
        # Keep the main step clear.
        ...

