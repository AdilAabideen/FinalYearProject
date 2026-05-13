#!/usr/bin/env python3
"""
Console runner for agents with colored, run_vitals_agent-style output.

Runs in-process (no FastAPI server required).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Optional

from langchain_core.messages import AIMessage, ToolMessage

from app.agentic.model_registry import get_chat_model, resolve_model_spec
from app.agentic.registry import get_agent_spec
from app.agentic.runtime import AgentRuntime


RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
GRAY = "\x1b[90m"


def _maybe_pretty_json(text: str) -> str:
    """Handle pretty json."""
    # Keep the main step clear.
    stripped = (text or "").strip()
    if not stripped:
        return ""
    try:
        obj = json.loads(stripped)
    except Exception:
        return stripped
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def _use_color() -> bool:
    """Handle color."""
    # Keep the main step clear.
    return (
        (os.environ.get("FORCE_COLOR") == "1" or sys.stdout.isatty())
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM") != "dumb"
    )


def _c(text: str, *codes: str) -> str:
    """Handle the value."""
    # Keep the main step clear.
    if not _use_color() or not codes:
        return text
    return "".join(codes) + text + RESET


def _status_color(status: str) -> str:
    """Handle color."""
    # Keep the main step clear.
    normalized = (status or "").strip().lower()
    if normalized in {"error", "failed", "failure"}:
        return RED
    if normalized in {"success", "ok"}:
        return GREEN
    return YELLOW


def _log(prefix: str, line: str) -> None:
    """Handle the value."""
    # Keep the main step clear.
    print(f"{prefix}{line}", flush=True)


def _log_block(prefix: str, header: str, body: str) -> None:
    """Handle block."""
    # Keep the main step clear.
    _log(prefix, header)
    if body:
        for ln in body.splitlines():
            _log(prefix, _c("  ", DIM, GRAY) + ln)
    print("", flush=True)


def _parse_tool_calls_from_text_jsonl(text: str) -> list[dict[str, Any]]:
    """
    Debug helper: if a model dumps tool calls as JSON/JSONL in plain text,
    try to extract them so you can see what's being attempted.
    """
    # Keep the output consistent.
    out: list[dict[str, Any]] = []
    raw = (text or "").strip()
    if not raw:
        return out

    candidates = [raw]
    if raw.startswith("```") and raw.endswith("```"):
        block = raw[3:-3].strip()
        if block.lower().startswith("json"):
            block = block[4:].strip()
        candidates.append(block)

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except Exception:
            obj = None

        if isinstance(obj, dict) and isinstance(obj.get("tool_calls"), list):
            for tc in obj["tool_calls"]:
                if isinstance(tc, dict):
                    out.append(tc)
            if out:
                return out

        for ln in cand.splitlines():
            line = ln.strip()
            if not line:
                continue
            try:
                obj2 = json.loads(line)
            except Exception:
                continue
            if isinstance(obj2, dict) and isinstance(obj2.get("tool_calls"), list):
                for tc in obj2["tool_calls"]:
                    if isinstance(tc, dict):
                        out.append(tc)
            elif isinstance(obj2, dict) and isinstance(obj2.get("name"), str):
                out.append(obj2)

        if out:
            return out

    return out


def _default_vitals_input() -> dict[str, Any]:
    """Handle vitals input."""
    # Keep the main step clear.
    return {
        "temperature": 98.5,
        "heartrate": 95.0,
        "resprate": 18.0,
        "o2sat": 100.0,
        "sbp": 160.0,
        "dbp": 54.0,
        "pain": 0.0,
        "subject_id": 13693875,
        "intime": "2156-12-17T17:47:00",
        "age_years": 82.96188547,
        "chiefcomplaint": "Dyspnea, Pedal edema",
    }


def main() -> int:
    """Handle the value."""
    # Keep the main step clear.
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="vitals_agent")
    ap.add_argument("--model", default=os.getenv("MODEL_ID", "medgemma-4b-it"))
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--input-json", default=None, help="Raw JSON string")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--show-raw-assistant", action="store_true")
    ap.add_argument(
        "--debug-parse-tool-json",
        action="store_true",
        help="Parse tool calls embedded in assistant text (debug visibility).",
    )
    args = ap.parse_args()

    if args.no_color:
        os.environ["NO_COLOR"] = "1"

    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            input_json = json.load(f)
    elif args.input_json:
        input_json = json.loads(args.input_json)
    else:
        input_json = _default_vitals_input()

    spec = get_agent_spec(args.agent)
    validated_input = spec.input_model.model_validate(input_json)

    model_id = args.model
    model_spec = resolve_model_spec(model_id)
    runtime = AgentRuntime(
        model_id=model_id,
        model_spec=model_spec,
        model=get_chat_model(model_id),
    )
    agent = spec.build(runtime)

    run_short = datetime.utcnow().strftime("%H%M%S")
    prefix = _c(f"[{args.agent}:{run_short}] ", DIM, GRAY)

    _log(prefix, _c("START", DIM, GRAY))
    _log(prefix, _c("MODEL", BOLD, CYAN) + f": {model_id}")
    _log_block(
        prefix,
        _c("INPUT", BOLD, CYAN),
        json.dumps(validated_input.model_dump(mode="json"), indent=2, ensure_ascii=False, default=str),
    )

    payload = {"messages": [("user", validated_input.model_dump_json())]}
    final_values: Optional[dict[str, Any]] = None

    for mode, data in agent.stream(payload, stream_mode=["updates", "values"]):
        if mode == "values":
            if isinstance(data, dict):
                final_values = data
            continue

        if mode != "updates" or not isinstance(data, dict):
            continue

        for node_name, node_update in data.items():
            if not isinstance(node_update, dict):
                continue
            messages = node_update.get("messages")
            if not isinstance(messages, list):
                continue

            for msg in messages:
                tool_calls = getattr(msg, "tool_calls", None) or []
                if tool_calls:
                    for tc in tool_calls:
                        if not isinstance(tc, dict):
                            continue
                        tool_name = tc.get("name") or "tool"
                        tool_call_id = tc.get("id")
                        args_obj = tc.get("args") or {}
                        suffix = f" ({tool_call_id})" if tool_call_id else ""
                        if tool_name == "log_thought":
                            thought = (args_obj or {}).get("thought", "")
                            _log_block(
                                prefix,
                                _c("THOUGHT", DIM, GRAY) + _c(suffix, DIM, GRAY),
                                _c(str(thought), DIM, GRAY),
                            )
                        else:
                            _log_block(
                                prefix,
                                f"{_c('TOOL CALL', BOLD, YELLOW)} {_c(tool_name, BOLD)}{_c(suffix, DIM, GRAY)}",
                                _maybe_pretty_json(json.dumps(args_obj, ensure_ascii=False, default=str)),
                            )
                    continue

                if isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, "name", None) or "tool"
                    status = getattr(msg, "status", None) or "ok"
                    tool_call_id = getattr(msg, "tool_call_id", None)
                    content = (getattr(msg, "content", "") or "").strip()
                    suffix = f" ({tool_call_id})" if tool_call_id else ""
                    if tool_name == "log_thought":
                        _log_block(
                            prefix,
                            _c("THOUGHT", DIM, GRAY) + _c(suffix, DIM, GRAY),
                            _c(content, DIM, GRAY),
                        )
                    else:
                        _log_block(
                            prefix,
                            f"{_c('RESULT', BOLD, CYAN)} {_c(tool_name, BOLD)} {_c(f'({status})', _status_color(status))}{_c(suffix, DIM, GRAY)}",
                            _maybe_pretty_json(content),
                        )
                    continue

                if isinstance(msg, AIMessage):
                    content = (getattr(msg, "content", "") or "").strip()
                    if not content:
                        continue

                    if args.debug_parse_tool_json:
                        parsed = _parse_tool_calls_from_text_jsonl(content)
                        if parsed:
                            _log_block(
                                prefix,
                                f"{_c('ASSISTANT (TEXT TOOL JSON)', BOLD, MAGENTA)} {node_name}",
                                _maybe_pretty_json(json.dumps(parsed, ensure_ascii=False, default=str)),
                            )
                            continue

                    if args.show_raw_assistant:
                        _log_block(
                            prefix,
                            f"{_c('ASSISTANT (RAW)', BOLD, MAGENTA)} {node_name}",
                            content,
                        )
                    else:
                        _log_block(
                            prefix,
                            f"{_c('ASSISTANT', BOLD, MAGENTA)} {node_name}",
                            _maybe_pretty_json(content),
                        )
                    continue

    if final_values is not None:
        maybe_structured = final_values.get("structured_response") if isinstance(final_values, dict) else None
        if maybe_structured is not None:
            _log_block(
                prefix,
                _c("STRUCTURED_RESPONSE", BOLD, GREEN),
                _maybe_pretty_json(json.dumps(maybe_structured, ensure_ascii=False, default=str)),
            )

    _log(prefix, _c("END", DIM, GRAY))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
