export type AgentTestCaseReadDto = {
  id: string;
  agent_name: string;
  name: string;
  enabled: boolean;
  input_json: Record<string, unknown>;
  expected_json: Record<string, unknown>;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentTestCaseRead = {
  id: string;
  agentName: string;
  name: string;
  enabled: boolean;
  inputJson: Record<string, unknown>;
  expectedJson: Record<string, unknown>;
  notes?: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AgentTestRunReadDto = {
  id: string;
  agent_name: string;
  name?: string | null;
  status: string;
  model_name?: string | null;
  selected_case_ids_json: string[];
  metrics_json?: Record<string, unknown> | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentTestRunRead = {
  id: string;
  agentName: string;
  name?: string | null;
  status: string;
  modelName?: string | null;
  selectedCaseIds: string[];
  metricsJson?: Record<string, unknown> | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AgentTestRunBatchSummaryDto = {
  status_counts?: Record<string, number>;
  passed_cases?: number;
  failed_cases?: number;
  completion_rate?: number | null;
  pass_rate_all?: number | null;
  pass_rate_completed?: number | null;
  exec_failed_cases?: number;
  invalid_pred_cases?: number;
};

export type AgentTestRunBatchLatencyDto = {
  min_ms?: number | null;
  p50_ms?: number | null;
  p95_ms?: number | null;
  max_ms?: number | null;
  avg_ms?: number | null;
};

export type AgentTestRunBatchScoreDto = {
  min?: number | null;
  max?: number | null;
  avg?: number | null;
};

export type AgentTestRunBatchCaseDto = Record<string, unknown> & {
  case_id?: string | null;
  test_case_id?: string | null;
  name?: string | null;
  status?: string | null;
  passed?: boolean | null;
  score?: number | null;
  latency_ms?: number | null;
  agent_status?: string | null;
  exec_failed?: boolean | number | null;
  invalid_pred?: boolean | number | null;
};

export type AgentTestRunBatchMetricsDto = {
  run: AgentTestRunReadDto;
  summary?: AgentTestRunBatchSummaryDto | null;
  latency?: AgentTestRunBatchLatencyDto | null;
  score?: AgentTestRunBatchScoreDto | null;
  cases?: AgentTestRunBatchCaseDto[] | null;
};

export type AgentTestRunBatchSummaryRead = {
  statusCounts: Record<string, number>;
  passedCases: number;
  failedCases: number;
  completionRate: number | null;
  passRateAll: number | null;
  passRateCompleted: number | null;
  execFailedCases: number;
  invalidPredCases: number;
};

export type AgentTestRunBatchLatencyRead = {
  minMs: number | null;
  p50Ms: number | null;
  p95Ms: number | null;
  maxMs: number | null;
  avgMs: number | null;
};

export type AgentTestRunBatchScoreRead = {
  min: number | null;
  max: number | null;
  avg: number | null;
};

export type AgentTestRunBatchCaseRead = {
  caseId: string | null;
  testCaseId: string | null;
  name: string | null;
  status: string | null;
  passed: boolean | null;
  score: number | null;
  latencyMs: number | null;
  agentStatus: string | null;
  execFailed: boolean | number | null;
  invalidPred: boolean | number | null;
  raw: Record<string, unknown>;
};

export type AgentTestRunBatchMetricsRead = {
  run: AgentTestRunRead;
  summary: AgentTestRunBatchSummaryRead;
  latency: AgentTestRunBatchLatencyRead;
  score: AgentTestRunBatchScoreRead;
  cases: AgentTestRunBatchCaseRead[];
};
