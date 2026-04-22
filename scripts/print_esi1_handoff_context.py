from __future__ import annotations

import sys
from pathlib import Path

from langchain_core.utils.function_calling import convert_to_openai_tool

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agentic.agents.esi1.handoffs import HANDOFFS
from app.agentic.agents.esi1.prompt import (
    HANDOFF_REQUIREMENTS,
    SINGLE_AGENT_OUTPUT_REQURIEMENTS,
    SYSTEM_PROMPT,
)
from app.agentic.handoff import create_handoff_tools
from app.agentic.protocols.prompt_protocol import build_system_prompt
from app.agentic.protocols.tool_protocol import build_tool_instruction


def main() -> None:
    handoff_tools = create_handoff_tools("esi1_agent", HANDOFFS)
    openai_tools = [convert_to_openai_tool(tool) for tool in handoff_tools]
    handoff_names = [tool.name for tool in handoff_tools]

    rendered = build_tool_instruction(
        openai_tools,
        tool_choice="any",
        multi_agent=True,
        handoff_names=handoff_names,
        final_answer_tool_name="final_answer",
        highlight_final_answer=True,
    )
    rendered_prompt = build_system_prompt(
        SYSTEM_PROMPT,
        multi_agent_addon=HANDOFF_REQUIREMENTS,
        single_agent_addon=SINGLE_AGENT_OUTPUT_REQURIEMENTS,
        multi_agent=True,
        extra_sections=[rendered],
    )

    print("=== ESI1 Handoff Tools ===")
    for tool in handoff_tools:
        print("- {name}".format(name=tool.name))

    print("\n=== Rendered Tool Context ===")
    print(rendered)

    print("\n=== Rendered Multi-Agent Prompt ===")
    print(rendered_prompt)


if __name__ == "__main__":
    main()
