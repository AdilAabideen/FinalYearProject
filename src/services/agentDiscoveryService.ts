import { API_BASE_URL } from '../config/env';
import type { AgentCatalogSummary, AgentCatalogSummaryDto } from '../types/agents';

export type AgentDiscoveryService = {
  listAgents: (signal?: AbortSignal) => Promise<AgentCatalogSummary[]>;
};

export const agentDiscoveryService: AgentDiscoveryService = {
  async listAgents(signal) {
    const response = await fetch(`${API_BASE_URL}/api/agents`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load agents');
    }

    const data = (await response.json()) as AgentCatalogSummaryDto[];

    return data.map((agent) => ({
      name: agent.name,
      title: agent.title,
      description: agent.description,
      toolsCount: agent.tools_count,
    }));
  },
};

