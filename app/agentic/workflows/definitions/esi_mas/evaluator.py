from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from app.agentic.eval_types import EvalResult
from app.agentic.mas_eval_types import WorkflowEvaluator

def _evaluate_expected_subset(
    expected: Dict[str, Any],
    actual: Optional[Dict[str, Any]],
) -> tuple[bool, float, Dict[str, Any]]:
    if actual is None:
        return False, 0.0, {"error": "actual_json_missing"}

    diffs: list[dict[str, Any]] = []

    def _walk(exp: Any, act: Any, path: str) -> None:
        if isinstance(exp, dict):
            if not isinstance(act, dict):
                diffs.append({"path": path, "expected": exp, "actual": act})
                return
            for key, value in exp.items():
                if key not in act:
                    diffs.append(
                        {
                            "path": f"{path}.{key}" if path else key,
                            "expected": value,
                            "actual": "__missing__",
                        }
                    )
                    continue
                _walk(value, act.get(key), f"{path}.{key}" if path else key)
            return

        if exp != act:
            diffs.append({"path": path, "expected": exp, "actual": act})

    _walk(expected, actual, "")
    passed = len(diffs) == 0
    return passed, (1.0 if passed else 0.0), {"diffs": diffs}


class ESIMASEvaluator(WorkflowEvaluator):
    label_name = "esi_mas_final_output_subset"

    def validate_expected(self, expected_json: Dict[str, Any]) -> None:
        if not isinstance(expected_json, dict):
            raise ValueError("expected_json must be an object")
        if "acuity" in expected_json:
            if set(expected_json.keys()) != {"acuity"}:
                raise ValueError("expected_json with acuity must only contain the acuity field")
            acuity = expected_json.get("acuity")
            if not isinstance(acuity, str) or acuity.strip() not in {"1", "2", "3", "4", "5"}:
                raise ValueError("expected_json.acuity must be a string between '1' and '5'")

    def evaluate(
        self,
        expected_json: Dict[str, Any],
        actual_json: Optional[Dict[str, Any]],
        *,
        mas_status: str,
    ) -> EvalResult:
        self.validate_expected(expected_json)

        if mas_status != "completed":
            return EvalResult(
                passed=False,
                score=0.0,
                diff_json={"error": "mas_not_completed", "mas_status": mas_status},
                metrics_json={
                    "label": self.label_name,
                    "mas_status": mas_status,
                    "exec_failed": True,
                    "missing_final_output": actual_json is None,
                },
            )

        if "acuity" in expected_json:
            actual_acuity = None
            if actual_json is not None:
                if "acuity" in actual_json:
                    actual_acuity = str(actual_json.get("acuity"))
                elif actual_json.get("final_esi_level") is not None:
                    actual_acuity = str(actual_json.get("final_esi_level"))
            passed = actual_acuity == str(expected_json.get("acuity"))
            return EvalResult(
                passed=passed,
                score=1.0 if passed else 0.0,
                diff_json=(
                    {}
                    if passed
                    else {
                        "expected": {"acuity": expected_json.get("acuity")},
                        "actual": {"acuity": actual_acuity},
                    }
                ),
                metrics_json={
                    "label": self.label_name,
                    "mas_status": mas_status,
                    "exec_failed": False,
                    "missing_final_output": actual_json is None,
                },
            )

        passed, score, diff_json = _evaluate_expected_subset(expected_json, actual_json)
        metrics_json = {
            "label": self.label_name,
            "mas_status": mas_status,
            "exec_failed": False,
            "missing_final_output": actual_json is None,
        }
        return EvalResult(
            passed=passed,
            score=score,
            diff_json=diff_json,
            metrics_json=metrics_json,
        )

    def aggregate(self, results: Sequence[EvalResult]) -> Dict[str, Any]:
        total = 0
        passed = 0
        exec_failed = 0
        missing_final_output = 0

        for result in results:
            total += 1
            if result.passed:
                passed += 1
            metrics = result.metrics_json or {}
            if metrics.get("exec_failed") is True:
                exec_failed += 1
            if metrics.get("missing_final_output") is True:
                missing_final_output += 1

        failed = total - passed
        pass_rate = round((passed / total), 4) if total else 0.0
        return {
            "label": self.label_name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "exec_failed": exec_failed,
            "missing_final_output": missing_final_output,
        }
