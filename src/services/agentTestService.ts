import { API_BASE_URL } from '../config/env';
import type {
  AgentTestRunBatchCaseDto,
  AgentTestRunBatchMetricsDto,
  AgentTestRunBatchMetricsRead,
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
    modelId?: string,
    signal?: AbortSignal,
  ) => Promise<AgentTestRunRead>;
  getRunBatchMetrics: (runId: string, signal?: AbortSignal) => Promise<AgentTestRunBatchMetricsRead>;
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

  async startTestRun(agentName, caseIds, name, modelId, signal) {
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
        model_id: modelId ?? null,
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

  async getRunBatchMetrics(runId, signal) {
    const url = `${API_BASE_URL}/api/tests/runs/${encodeURIComponent(runId)}/metrics`;
    const response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load aggregated run metrics');
    }

    const data = (await response.json()) as AgentTestRunBatchMetricsDto;
    const run = data.run;
    const summary = data.summary ?? {};
    const latency = data.latency ?? {};
    const score = data.score ?? {};
    const cases = Array.isArray(data.cases) ? data.cases : [];

    return {
      run: {
        id: run.id,
        agentName: run.agent_name,
        name: run.name ?? null,
        status: run.status,
        modelName: run.model_name ?? null,
        selectedCaseIds: run.selected_case_ids_json,
        metricsJson: run.metrics_json ?? null,
        startedAt: run.started_at ?? null,
        finishedAt: run.finished_at ?? null,
        createdAt: run.created_at,
        updatedAt: run.updated_at,
      },
      summary: {
        statusCounts: summary.status_counts ?? {},
        passedCases: summary.passed_cases ?? 0,
        failedCases: summary.failed_cases ?? 0,
        completionRate: summary.completion_rate ?? null,
        passRateAll: summary.pass_rate_all ?? null,
        passRateCompleted: summary.pass_rate_completed ?? null,
        execFailedCases: summary.exec_failed_cases ?? 0,
        invalidPredCases: summary.invalid_pred_cases ?? 0,
      },
      latency: {
        minMs: latency.min_ms ?? null,
        p50Ms: latency.p50_ms ?? null,
        p95Ms: latency.p95_ms ?? null,
        maxMs: latency.max_ms ?? null,
        avgMs: latency.avg_ms ?? null,
      },
      score: {
        min: score.min ?? null,
        max: score.max ?? null,
        avg: score.avg ?? null,
      },
      cases: cases.map((item) => {
        const row = item as AgentTestRunBatchCaseDto;
        return {
          caseId: row.case_id ?? null,
          testCaseId: row.test_case_id ?? null,
          name: row.name ?? null,
          status: row.status ?? null,
          passed: typeof row.passed === 'boolean' ? row.passed : null,
          score: typeof row.score === 'number' ? row.score : null,
          latencyMs: typeof row.latency_ms === 'number' ? row.latency_ms : null,
          agentStatus: row.agent_status ?? null,
          execFailed:
            typeof row.exec_failed === 'boolean' || typeof row.exec_failed === 'number'
              ? row.exec_failed
              : null,
          invalidPred:
            typeof row.invalid_pred === 'boolean' || typeof row.invalid_pred === 'number'
              ? row.invalid_pred
              : null,
          raw: item,
        };
      }),
    };
  },
};
