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


def _print_mermaid(workflow) -> None:
    print("\nMermaid diagram:")
    print("```mermaid")
    print("flowchart LR")
    print("  START([START])")
    print("  END([END])")

    for agent_name in workflow.participating_agents:
        print('  {agent}["{agent}"]'.format(agent=agent_name))

    for gate_id in workflow.gate_ids:
        print('  {gate}{{"{gate}"}}'.format(gate=gate_id))

    for agent_name in workflow.start_agents:
        print("  START --> {agent}".format(agent=agent_name))

    for source_node, target_node in workflow.graph_edges():
        print("  {source} --> {target}".format(source=source_node, target=target_node))

    for agent_name in workflow.finalizing_agents:
        print("  {agent} --> END".format(agent=agent_name))

    print("```")


def _print_text_topology(workflow) -> None:
    print("\nText topology:")
    print("START")
    for agent_name in workflow.start_agents:
        print("  -> {agent}".format(agent=agent_name))
    for source_node, target_node in workflow.graph_edges():
        print("{source} -> {target}".format(source=source_node, target=target_node))
    for agent_name in workflow.finalizing_agents:
        print("{agent} -> END".format(agent=agent_name))


def main() -> None:
    workflow = get_workflow_definition("esi_mas")

    print("=== Workflow Definition ===")
    print("id:", workflow.metadata.workflow_id)
    print("name:", workflow.metadata.name)
    print("version:", workflow.metadata.version)
    print("description:", workflow.metadata.description or "")

    print("\nParticipating agents:")
    for agent_name in workflow.participating_agents:
        print("- {agent} {metadata}".format(agent=agent_name, metadata=_json(workflow.agent_metadata.get(agent_name, {}))))

    print("\nSources:")
    for source_id in workflow.source_ids:
        source = workflow.sources[source_id]
        print("- {source_id}".format(source_id=source_id))
        print("  name:", source.name)
        print("  agent_names:", list(source.agent_names))
        print("  metadata:", _json(source.metadata))

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
        print("  incoming_from:", list(workflow.gate_incoming_nodes(gate_id)))
        print("  target_node:", gate.target_node)
        print("  source_to_agents:")
        for source_id in gate.required_sources:
            print("    {source}: {agents}".format(source=source_id, agents=list(workflow.source_agents(source_id))))
        print("  metadata:", _json(gate.metadata))

    print("\nGraph edges:")
    for source_node, target_node in workflow.graph_edges():
        print("- {source} -> {target}".format(source=source_node, target=target_node))

    print("\nWorkflow metadata:")
    print(_json(workflow.workflow_metadata))

    _print_mermaid(workflow)
    _print_text_topology(workflow)


if __name__ == "__main__":
    main()
