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

