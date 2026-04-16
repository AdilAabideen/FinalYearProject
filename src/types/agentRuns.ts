export type RunStatus = string;

export type AgentRunMetrics = {
  id: string;
  tokens_total?: number;
  input_tokens_total?: number;
  llm_call_count?: number;
  output_tokens_total?: number;
  status: string;
  tool_error_count?: number;
  tool_call_count?: number;
  failure_reason?: string | null;
  duration_seconds?: number;
  cost_usd_total?: number;
}

export type AgentRunMetricsDto = {
  run_id: string;
  agent_system: string;
  agent_name: string;
  model_name: string;
  status: string;
  failure_reason: string | null;
  duration_ms?: number;
  llm_call_count?: number;
  tool_call_count?: number;
  tool_error_count?: number;
  input_tokens_total?: number;
  output_tokens_total?: number;
  tokens_total?: number;
  cost_usd_total?: number;
  schema_valid?: boolean;
  created_at?: string;
  updated_at?: string;
};

export type AgentRunMetricsResponseDto = {
  run_id: string;
  metrics: AgentRunMetricsDto | null;
  llm_calls?: unknown[];
};

export type AgentRunReadDto = {
  id: string;
  agent_name: string;
  status: RunStatus;
  model_name?: string | null;
  input_json: Record<string, unknown>;
  output_json?: Record<string, unknown> | null;
  error_text?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentRunRead = {
  id: string;
  agentName: string;
  status: RunStatus;
  modelName?: string | null;
  inputJson: Record<string, unknown>;
  outputJson?: Record<string, unknown> | null;
  errorText?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt: string;
  updatedAt: string;
};
