export type MasWorkflowSummaryDto = {
  workflow_id: string;
  name: string;
  version: string;
  description: string;
  participating_agents_count: number;
  start_agents_count: number;
  finalizing_agents_count: number;
  gates_count: number;
  sources_count: number;
};

export type MasWorkflowSummary = {
  workflowId: string;
  name: string;
  version: string;
  description: string;
  participatingAgentsCount: number;
  startAgentsCount: number;
  finalizingAgentsCount: number;
  gatesCount: number;
  sourcesCount: number;
};

export type MasWorkflowMetadataRead = {
  workflow_id: string;
  name: string;
  version: string;
  description: string;
};

export type MasSourceRead = {
  source_id: string;
  name: string;
  agent_names: string[];
  description: string;
  metadata: Record<string, unknown>;
};

export type MasGateRead = {
  gate_id: string;
  name: string;
  description: string;
  required_sources: string[];
  incoming_from: string[];
  target_node: string;
  metadata: Record<string, unknown>;
};

export type MasCatalogDetail = {
  metadata: MasWorkflowMetadataRead;
  participating_agents: string[];
  start_agents: string[];
  finalizing_agents: string[];
  allowed_handoffs: Record<string, string[]>;
  sources: Record<string, MasSourceRead>;
  gates: Record<string, MasGateRead>;
  agent_metadata: Record<string, Record<string, unknown>>;
  workflow_metadata: Record<string, unknown>;
};
