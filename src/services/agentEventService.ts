// Calls the agent event service API.
import { API_BASE_URL } from '../config/env';
import type { AgentEventsPage, AgentEventsPageDto } from '../types/agentEvents';

export type ListAgentEventsParams = {
  afterSeq?: number;
  limit?: number;
};

export type AgentEventService = {
  listAgentEvents: (
    runId: string,
    params?: ListAgentEventsParams,
    signal?: AbortSignal,
  ) => Promise<AgentEventsPage>;
};

export const agentEventService: AgentEventService = {
// Lists agent events.
  async listAgentEvents(runId, params, signal) {
    const search = new URLSearchParams();
    if (typeof params?.afterSeq === 'number') search.set('after_seq', String(params.afterSeq));
    if (typeof params?.limit === 'number') search.set('limit', String(params.limit));

    const query = search.toString();
    const url = `${API_BASE_URL}/api/agent-runs/${encodeURIComponent(runId)}/events${query ? `?${query}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load agent events');
    }

    const data = (await response.json()) as AgentEventsPageDto;

    return {
      runId: data.run_id,
      nextAfterSeq: data.next_after_seq,
// Maps logic.
      events: data.events.map((event) => ({
        id: event.id,
        runId: event.run_id,
        agentName: event.agent_name,
        seq: event.seq,
        eventType: event.event_type,
        nodeName: event.node_name ?? null,
        toolName: event.tool_name ?? null,
        toolCallId: event.tool_call_id ?? null,
        status: event.status ?? null,
        payloadJson: event.payload_json ?? null,
        payloadText: event.payload_text ?? null,
        createdAt: event.created_at,
      })),
    };
  },
};

