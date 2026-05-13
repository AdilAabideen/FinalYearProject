// Defines agent tests types.
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
  total_runs?: number;
  runs_with_agent_run?: number;
  successful_runs?: number;
  failed_runs?: number;
  success_rate?: number | null;
  missing_metrics_count?: number;
  llm_call_count_total?: number;
  tool_call_count_total?: number;
  tool_error_count_total?: number;
  input_tokens_total?: number;
  output_tokens_total?: number;
  tokens_total?: number;
  duration_ms_total?: number;
  cost_usd_total?: number;
  llm_call_count_avg?: number;
  tool_call_count_avg?: number;
  tool_error_count_avg?: number;
  input_tokens_avg?: number;
  output_tokens_avg?: number;
  tokens_avg?: number;
  duration_ms_avg?: number;
  cost_usd_avg?: number;
  cost_usd_avg_successful?: number | null;
  failure_reason_counts?: Record<string, number>;
};

export type AgentTestRunBatchCaseDto = Record<string, unknown> & {
  case_id?: string | null;
  test_case_id?: string | null;
  test_case_name?: string | null;
  agent_run_id?: string | null;
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
  cases?: AgentTestRunBatchCaseDto[] | null;
};

export type AgentTestRunBatchSummaryRead = {
  totalRuns: number;
  runsWithAgentRun: number;
  successfulRuns: number;
  failedRuns: number;
  successRate: number | null;
  missingMetricsCount: number;
  llmCallCountTotal: number;
  toolCallCountTotal: number;
  toolErrorCountTotal: number;
  inputTokensTotal: number;
  outputTokensTotal: number;
  tokensTotal: number;
  durationMsTotal: number;
  costUsdTotal: number;
  llmCallCountAvg: number;
  toolCallCountAvg: number;
  toolErrorCountAvg: number;
  inputTokensAvg: number;
  outputTokensAvg: number;
  tokensAvg: number;
  durationMsAvg: number;
  costUsdAvg: number;
  costUsdAvgSuccessful: number | null;
  failureReasonCounts: Record<string, number>;
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
  cases: AgentTestRunBatchCaseRead[];
};
