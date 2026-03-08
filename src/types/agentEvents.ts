export type AgentEventReadDto = {
  id: number;
  run_id: string;
  agent_name: string;
  seq: number;
  event_type: string;
  node_name?: string | null;
  tool_name?: string | null;
  tool_call_id?: string | null;
  status?: string | null;
  payload_json?: Record<string, unknown> | null;
  payload_text?: string | null;
  created_at: string;
};

export type AgentEventRead = {
  id: number;
  runId: string;
  agentName: string;
  seq: number;
  eventType: string;
  nodeName?: string | null;
  toolName?: string | null;
  toolCallId?: string | null;
  status?: string | null;
  payloadJson?: Record<string, unknown> | null;
  payloadText?: string | null;
  createdAt: string;
};

export type AgentEventsPageDto = {
  run_id: string;
  events: AgentEventReadDto[];
  next_after_seq: number;
};

export type AgentEventsPage = {
  runId: string;
  events: AgentEventRead[];
  nextAfterSeq: number;
};

