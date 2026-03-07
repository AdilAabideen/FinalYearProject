import { API_BASE_URL } from '../config/env';
import type {
  AgentCatalogDetail,
  AgentCatalogDetailDto,
  AgentCatalogSummary,
  AgentCatalogSummaryDto,
} from '../types/agents';

export type AgentDiscoveryService = {
  listAgents: (signal?: AbortSignal) => Promise<AgentCatalogSummary[]>;
  getAgent: (agentName: string, signal?: AbortSignal) => Promise<AgentCatalogDetail>;
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

  async getAgent(agentName, signal) {
    const response = await fetch(
      `${API_BASE_URL}/api/agents/${encodeURIComponent(agentName)}`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        signal,
      },
    );

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Failed to load agent (${agentName})`);
    }

    const data = (await response.json()) as AgentCatalogDetailDto;

    return {
      name: data.name,
      title: data.title,
      description: data.description,
      inputSchema: data.input_schema,
      tools: data.tools.map((tool) => ({
        name: tool.name,
        description: tool.description,
        argsSchema: tool.args_schema,
      })),
    } satisfies AgentCatalogDetail;
  },
};
