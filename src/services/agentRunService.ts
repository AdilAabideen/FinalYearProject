import { API_BASE_URL } from '../config/env';
import type {
  AgentRunMetrics,
  AgentRunMetricsResponseDto,
  AgentRunRead,
  AgentRunReadDto,
  RunStatus,
} from '../types/agentRuns';

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
  getAgentRunMetrics: (runId: string, signal?: AbortSignal) => Promise<AgentRunMetrics>;
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

  async getAgentRunMetrics(runId, signal) {
    const response = await fetch(`${API_BASE_URL}/api/agent-runs/${encodeURIComponent(runId)}/metrics`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
    
    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load agent run metrics');
    }

    const data = (await response.json()) as AgentRunMetricsResponseDto;
    const metrics = data.metrics;
    if (!metrics) {
      throw new Error('Metrics were not returned for this run');
    }

    const reliabilitySummary =
      data.reliability_summary == null
        ? null
        : {
          totalIssues: data.reliability_summary.total_issues,
          errorIssues: data.reliability_summary.error_issues,
          byCode: data.reliability_summary.by_code.map((item) => ({
            issueCode: item.issue_code,
            count: item.count,
          })),
        };

    const return_metrics: AgentRunMetrics = {
      id: metrics.run_id,
      tokens_total: metrics.tokens_total,
      input_tokens_total: metrics.input_tokens_total,
      llm_call_count: metrics.llm_call_count,
      output_tokens_total: metrics.output_tokens_total,
      status: metrics.status,
      tool_error_count: metrics.tool_error_count,
      tool_call_count: metrics.tool_call_count,
      duration_seconds:
        typeof metrics.duration_ms === 'number' ? metrics.duration_ms / 1000 : undefined,
      cost_usd_total: metrics.cost_usd_total,
      reliabilitySummary,
    };



    return {
      ...return_metrics,
      ...(metrics.failure_reason != null ? { failure_reason: metrics.failure_reason } : {}),
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
