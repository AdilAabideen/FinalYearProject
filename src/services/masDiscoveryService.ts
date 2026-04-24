import { API_BASE_URL } from '../config/env';
import type { MasCatalogDetail, MasWorkflowSummary, MasWorkflowSummaryDto } from '../types/mas';

export type MasDiscoveryService = {
  listMas: (signal?: AbortSignal) => Promise<MasWorkflowSummary[]>;
  getWorkflow: (workflowId: string, signal?: AbortSignal) => Promise<MasCatalogDetail>;
};

export const masDiscoveryService: MasDiscoveryService = {
  async listMas(signal) {
    const response = await fetch(`${API_BASE_URL}/api/mas`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load workflows');
    }

    const data = (await response.json()) as MasWorkflowSummaryDto[];

    return data.map((workflow) => ({
      workflowId: workflow.workflow_id,
      name: workflow.name,
      version: workflow.version,
      description: workflow.description,
      participatingAgentsCount: workflow.participating_agents_count,
      startAgentsCount: workflow.start_agents_count,
      finalizingAgentsCount: workflow.finalizing_agents_count,
      gatesCount: workflow.gates_count,
      sourcesCount: workflow.sources_count,
    }));
  },

  async getWorkflow(workflowId, signal) {
    const response = await fetch(`${API_BASE_URL}/api/mas/${encodeURIComponent(workflowId)}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Failed to load workflow (${workflowId})`);
    }

    return (await response.json()) as MasCatalogDetail;
  },
};
