export type RunStatus = string;

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

