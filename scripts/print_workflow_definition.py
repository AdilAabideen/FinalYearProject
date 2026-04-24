from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agentic.workflows.registry import get_workflow_definition


def _json(data):
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def main() -> None:
    workflow = get_workflow_definition("esi_swarm_v1")

    print("=== Workflow Definition ===")
    print("id:", workflow.metadata.workflow_id)
    print("name:", workflow.metadata.name)
    print("version:", workflow.metadata.version)
    print("description:", workflow.metadata.description or "")

    print("\nParticipating agents:")
    for agent_name in workflow.participating_agents:
        print("- {agent} {metadata}".format(agent=agent_name, metadata=_json(workflow.agent_metadata.get(agent_name, {}))))

    print("\nStart agents:")
    for agent_name in workflow.start_agents:
        print("- {agent}".format(agent=agent_name))

    print("\nFinalizing agents:")
    for agent_name in workflow.finalizing_agents:
        print("- {agent}".format(agent=agent_name))

    print("\nAllowed handoffs:")
    for source_agent in workflow.participating_agents:
        targets = workflow.allowed_targets_for(source_agent)
        if not targets:
            print("- {source} -> none".format(source=source_agent))
            continue
        for target_agent in targets:
            print("- {source} -> {target}".format(source=source_agent, target=target_agent))

    print("\nGate nodes:")
    for gate_id, gate in workflow.gates.items():
        print("- {gate_id}".format(gate_id=gate_id))
        print("  name:", gate.name)
        print("  required_sources:", list(gate.required_sources))
        print("  incoming_from:", list(gate.incoming_from))
        print("  target_node:", gate.target_node)
        print("  metadata:", _json(gate.metadata))

    print("\nGraph edges:")
    for source_node, target_node in workflow.graph_edges():
        print("- {source} -> {target}".format(source=source_node, target=target_node))

    print("\nWorkflow metadata:")
    print(_json(workflow.workflow_metadata))


if __name__ == "__main__":
    main()
