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
