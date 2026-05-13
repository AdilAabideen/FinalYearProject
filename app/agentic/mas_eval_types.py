from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Sequence

from app.agentic.eval_types import EvalResult


class WorkflowEvaluator(Protocol):
    def validate_expected(self, expected_json: Dict[str, Any]) -> None:
        ...

    def evaluate(
        self,
        expected_json: Dict[str, Any],
        actual_json: Optional[Dict[str, Any]],
        *,
        mas_status: str,
    ) -> EvalResult:
        ...

    def aggregate(self, results: Sequence[EvalResult]) -> Dict[str, Any]:
        ...
