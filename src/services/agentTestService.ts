import { API_BASE_URL } from '../config/env';
import type {
  AgentTestCaseRead,
  AgentTestCaseReadDto,
  AgentTestRunRead,
  AgentTestRunReadDto,
} from '../types/agentTests';

export type ListAgentTestCasesParams = {
  agentName?: string;
  enabled?: boolean;
  limit?: number;
  offset?: number;
  order?: 'asc' | 'desc';
};

export type AgentTestService = {
  listTestCases: (
    params?: ListAgentTestCasesParams,
    signal?: AbortSignal,
  ) => Promise<AgentTestCaseRead[]>;
  startTestRun: (
    agentName: string,
    caseIds: string[],
    name?: string,
    signal?: AbortSignal,
  ) => Promise<AgentTestRunRead>;
};

export const agentTestService: AgentTestService = {
  async listTestCases(params, signal) {
    const search = new URLSearchParams();
    if (params?.agentName) search.set('agent_name', params.agentName);
    if (typeof params?.enabled === 'boolean') search.set('enabled', String(params.enabled));
    if (typeof params?.limit === 'number') search.set('limit', String(params.limit));
    if (typeof params?.offset === 'number') search.set('offset', String(params.offset));
    if (params?.order) search.set('order', params.order);

    const query = search.toString();
    const url = `${API_BASE_URL}/api/tests/cases${query ? `?${query}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load test cases');
    }

    const data = (await response.json()) as AgentTestCaseReadDto[];

    return data.map((row) => ({
      id: row.id,
      agentName: row.agent_name,
      name: row.name,
      enabled: row.enabled,
      inputJson: row.input_json,
      expectedJson: row.expected_json,
      notes: row.notes ?? null,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    }));
  },

  async startTestRun(agentName, caseIds, name, signal) {
    const url = `${API_BASE_URL}/api/tests/runs/start`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        agent_name: agentName,
        name: name ?? null,
        case_ids: caseIds,
      }),
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to start test run');
    }

    const data = (await response.json()) as AgentTestRunReadDto;

    return {
      id: data.id,
      agentName: data.agent_name,
      name: data.name ?? null,
      status: data.status,
      modelName: data.model_name ?? null,
      selectedCaseIds: data.selected_case_ids_json,
      metricsJson: data.metrics_json ?? null,
      startedAt: data.started_at ?? null,
      finishedAt: data.finished_at ?? null,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
    };
  },
};

