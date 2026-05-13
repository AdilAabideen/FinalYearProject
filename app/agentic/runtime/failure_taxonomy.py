"""Failure Taxonomy module helpers."""

from __future__ import annotations

from enum import Enum


class FailureCategory(str, Enum):
    """Standardized failure/reliability categories for runtime analysis."""

    PROVIDER_ERROR = "provider_error"
    TIMEOUT_ERROR = "timeout_error"
    NATIVE_TOOL_PARSE_FAILURE = "native_tool_parse_failure"
    TEXT_RECOVERY_USED = "text_recovery_used"
    TEXT_RECOVERY_FAILURE = "text_recovery_failure"
    UNKNOWN_TOOL = "unknown_tool"
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    FINAL_OUTPUT_MISSING = "final_output_missing"
    FINAL_OUTPUT_INVALID = "final_output_invalid"
    SCHEMA_VALIDATION_ERROR = "schema_validation_error"
    EXTRA_TOOL_CALLS_DROPPED = "extra_tool_calls_dropped"

