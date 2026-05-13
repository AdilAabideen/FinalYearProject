// Provides MAS traces helpers.
import type { Dispatch, SetStateAction } from 'react';
import type { EventStreamPayload, SwarmEventType } from '../../../types/masRuns';
import type { AgentRunMetrics } from '../../../types/agentRuns';

export type MasEventTypes =
  | 'Swarm Started'
  | 'Swarm Ended'
  | 'Agent Execution Started'
  | 'Agent Execution Finished'
  | 'Swarm Error'
  | 'Handoff'
  | 'Gate Evaluated'
  | 'Final Output Created';

export type ArchType = 'MAS' | 'Agent';

export type MasGeneralEvent = {
  event_type: MasEventTypes;
  arch_type: ArchType;
  description: string;
  created_at: string;
};

export type MetricsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; metrics: AgentRunMetrics };

// Checks record.
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// Casts nullable string.
function asNullableString(value: unknown): string | null {
  return typeof value === 'string' ? value : value === null ? null : null;
}

// Casts event type.
function asEventType(value: unknown): SwarmEventType | null {
  if (
    value === 'swarm_started' ||
    value === 'swarm_failed' ||
    value === 'agent_started' ||
    value === 'handoff_created' ||
    value === 'agent_completed' ||
    value === 'gate_evaluated' ||
    value === 'final_output_created' ||
    value === 'swarm_completed'
  ) {
    return value;
  }
  return null;
}

// Parses event stream payload.
export function parseEventStreamPayload(value: unknown): EventStreamPayload | null {
  if (!isRecord(value)) return null;

  const eventType = asEventType(value.event_type);
  if (!eventType) return null;
  if (typeof value.id !== 'number') return null;
  if (typeof value.swarm_run_id !== 'string') return null;
  if (typeof value.seq !== 'number') return null;
  if (typeof value.workflow_id !== 'string') return null;
  if (typeof value.created_at !== 'string') return null;

  return {
    id: value.id,
    swarm_run_id: value.swarm_run_id,
    seq: value.seq,
    event_type: eventType,
    workflow_id: value.workflow_id,
    agent_run_id: asNullableString(value.agent_run_id),
    agent_name: asNullableString(value.agent_name),
    handoff_id: asNullableString(value.handoff_id),
    gate_evaluation_id: asNullableString(value.gate_evaluation_id),
    final_output_id: asNullableString(value.final_output_id),
    status: typeof value.status === 'string' ? value.status : '',
    payload_json: isRecord(value.payload_json) ? value.payload_json : null,
    payload_text: asNullableString(value.payload_text),
    created_at: value.created_at,
  };
}

// Builds initial agent run IDS.
export function buildInitialAgentRunIds(agentNames: string[]) {
  const next: Record<string, string | null> = {};
  for (const agentName of agentNames) next[agentName] = null;
  return next;
}

// Appends general event.
export function appendGeneralEvent(
  setGeneralEvents: Dispatch<SetStateAction<MasGeneralEvent[]>>,
  event: MasGeneralEvent,
) {
// Sets general events.
  setGeneralEvents((prev) => [...prev, event]);
}

// Formats trace timestamp.
export function formatTraceTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

// Normalizes output value.
export function normalizeOutputValue(value: unknown) {
  if (value == null) return null;
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }

  return value;
}
