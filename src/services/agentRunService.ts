import { API_BASE_URL } from '../config/env';
import type { AgentRunRead, AgentRunReadDto, RunStatus } from '../types/agentRuns';

export type ListAgentRunsParams = {
  agentName?: string;
  status?: RunStatus;
  limit?: number;
  offset?: number;
  order?: 'asc' | 'desc';
};

export type AgentRunService = {
  listAgentRuns: (params?: ListAgentRunsParams, signal?: AbortSignal) => Promise<AgentRunRead[]>;
  getAgentRun: (runId: string, signal?: AbortSignal) => Promise<AgentRunRead>;
  startAgentRun: (
    agentName: string,
    input: Record<string, unknown>,
    modelId?: string,
    signal?: AbortSignal,
  ) => Promise<{ runId: string; status: RunStatus }>;
};

export const agentRunService: AgentRunService = {
  async listAgentRuns(params, signal) {
    const search = new URLSearchParams();
    if (params?.agentName) search.set('agent_name', params.agentName);
    if (params?.status) search.set('status', params.status);
    if (params?.limit) search.set('limit', String(params.limit));
    if (params?.offset) search.set('offset', String(params.offset));
    if (params?.order) search.set('order', params.order);

    const query = search.toString();
    const url = `${API_BASE_URL}/api/agent-runs${query ? `?${query}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load agent runs');
    }

    const data = (await response.json()) as AgentRunReadDto[];

    return data.map((run) => ({
      id: run.id,
      agentName: run.agent_name,
      status: run.status,
      modelName: run.model_name ?? null,
      inputJson: run.input_json,
      outputJson: run.output_json ?? null,
      errorText: run.error_text ?? null,
      startedAt: run.started_at ?? null,
      finishedAt: run.finished_at ?? null,
      createdAt: run.created_at,
      updatedAt: run.updated_at,
    }));
  },

  async getAgentRun(runId, signal) {
    const response = await fetch(`${API_BASE_URL}/api/agent-runs/${encodeURIComponent(runId)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load agent run');
    }

    const run = (await response.json()) as AgentRunReadDto;

    return {
      id: run.id,
      agentName: run.agent_name,
      status: run.status,
      modelName: run.model_name ?? null,
      inputJson: run.input_json,
      outputJson: run.output_json ?? null,
      errorText: run.error_text ?? null,
      startedAt: run.started_at ?? null,
      finishedAt: run.finished_at ?? null,
      createdAt: run.created_at,
      updatedAt: run.updated_at,
    };
  },

  async startAgentRun(agentName, input, modelId, signal) {
    const response = await fetch(`${API_BASE_URL}/api/agent-runs/start`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ agent_name: agentName, model_id: modelId ?? null, input }),
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to start agent run');
    }

    const data = (await response.json()) as { run_id: string; status: RunStatus };
    return { runId: data.run_id, status: data.status };
  },
};
