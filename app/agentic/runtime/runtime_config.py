from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RuntimeConfig:
    """Central runtime policy switches for hand-rolled agent execution."""

    max_tool_calls_per_turn: int = 2
    require_final_answer_tool: bool = True
    allow_text_tool_recovery: bool = True
    allow_plain_json_final_output: bool = False
    structured_output_fallback_enabled: bool = False
    drop_extra_tool_calls: bool = True

    def __post_init__(self) -> None:
        if self.max_tool_calls_per_turn < 1:
            raise ValueError("max_tool_calls_per_turn must be >= 1.")

    def to_dict(self) -> dict[str, object]:
        """Return a serializable dict for telemetry and experiment logging."""
        return asdict(self)
