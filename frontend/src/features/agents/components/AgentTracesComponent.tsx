import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { API_BASE_URL } from '../../../config/env';
import { classifyToolStatus } from '../utils/status';
import { isLogThoughtTool, tryParseJson } from '../utils/trace';
import { AgentTraceEntries, type TraceEntry } from './agent-traces/AgentTraceEntries';

type AgentTracesComponentProps = {
  runId: string;
  onDone?: (runId: string) => void;
};

type StreamState = 'connecting' | 'open' | 'done' | 'error';

type AgentEventPayload = {
  seq?: number | string;
  event_type?: string;
  node_name?: string;
  tool_name?: string;
  tool_call_id?: string;
  status?: string;
  payload_json?: unknown;
  payload_text?: string;
  created_at?: string;
};

// Checks record.
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// Casts agent event payload.
function asAgentEventPayload(value: unknown): AgentEventPayload {
  if (!isRecord(value)) return {};
  return {
    seq: typeof value.seq === 'number' || typeof value.seq === 'string' ? value.seq : undefined,
    event_type: typeof value.event_type === 'string' ? value.event_type : undefined,
    node_name: typeof value.node_name === 'string' ? value.node_name : undefined,
    tool_name: typeof value.tool_name === 'string' ? value.tool_name : undefined,
    tool_call_id: typeof value.tool_call_id === 'string' ? value.tool_call_id : undefined,
    status: typeof value.status === 'string' ? value.status : undefined,
    payload_json: 'payload_json' in value ? value.payload_json : undefined,
    payload_text: typeof value.payload_text === 'string' ? value.payload_text : undefined,
    created_at: typeof value.created_at === 'string' ? value.created_at : undefined,
  };
}

// Gets tool output value.
function getToolOutputValue(payload: AgentEventPayload) {
  if (payload.payload_json != null) return payload.payload_json;
  if (payload.payload_text != null) return tryParseJson(payload.payload_text);
  return null;
}

// Renders the agent traces component.
export function AgentTracesComponent({ runId, onDone }: AgentTracesComponentProps) {
  const [streamState, setStreamState] = useState<StreamState>('connecting');
  const [errorText, setErrorText] = useState<string | null>(null);
  const [entries, setEntries] = useState<TraceEntry[]>([]);
  const sourceRef = useRef<EventSource | null>(null);
  const entryIdRef = useRef(0);
  const seenEventIdsRef = useRef<Set<number>>(new Set());
  const onDoneRef = useRef(onDone);

  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  const streamUrl = useMemo(() => {
    const base = API_BASE_URL ? API_BASE_URL : '';
    return `${base}/api/agent-runs/${encodeURIComponent(runId)}/events/stream`;
  }, [runId]);

// Manages callback.
  const handleOpen = useCallback(() => {
    setStreamState('open');
    setErrorText(null);
  }, []);

// Manages callback.
  const handleError = useCallback(() => {
    setStreamState((prev) => (prev === 'done' ? 'done' : 'connecting'));
  }, []);

// Manages callback.
  const handleMessage = useCallback((event: MessageEvent<string>) => {
    void event;
  }, []);

// Manages callback.
  const handleDone = useCallback((event: MessageEvent<string>) => {
    void event;
    setStreamState('done');
    sourceRef.current?.close();
    onDoneRef.current?.(runId);
  }, [runId]);

// Manages callback.
  const handleAgentEvent = useCallback((event: MessageEvent<string>) => {
    try {
      const eventId = Number(event.lastEventId);
      if (Number.isFinite(eventId)) {
        if (seenEventIdsRef.current.has(eventId)) return;
        seenEventIdsRef.current.add(eventId);
      }
      const parsed = JSON.parse(event.data) as unknown;
      const payload = asAgentEventPayload(parsed);

      if (payload.event_type !== 'tool_result' && payload.event_type !== 'thought') return;
      if (!payload.tool_name) return;

      const output = getToolOutputValue(payload);
      const status = classifyToolStatus(payload.status);

      const hasOutput = output != null && (typeof output !== 'string' || output.trim().length > 0);

      entryIdRef.current += 1;
      const idSuffix = event.lastEventId ? `${event.lastEventId}` : `evt-${Date.now()}`;
      const entryId = `${idSuffix}-${entryIdRef.current}`;

      if (payload.event_type === 'thought' || isLogThoughtTool(payload.tool_name)) {
        let step = '';
        let thought = '';

        if (isRecord(payload.payload_json)) {
          const resultRecord = isRecord(payload.payload_json.result)
            ? payload.payload_json.result
            : payload.payload_json;
          step = typeof resultRecord.step === 'string' ? resultRecord.step : '';
          thought = typeof resultRecord.thought === 'string' ? resultRecord.thought : '';
        }

        if (!thought && typeof payload.payload_text === 'string') {
          thought = payload.payload_text.trim();
        }
        if (!step && !thought) return;

        setEntries((prev) => [
          ...prev,
          {
            id: entryId,
            kind: 'thinking',
            output: {
              step: step || 'Thought',
              thought: thought || 'No thought content.',
            },
          },
        ]);
        return;
      }

      if (!hasOutput && status === 'unknown') return;


      setEntries((prev) => [
        ...prev,
        {
          id: entryId,
          kind: 'action',
          toolName: payload.tool_name ?? 'Tool',
          status,
          output,
        },
      ]);
    } catch {
    }
  }, []);

  useEffect(() => {
    sourceRef.current?.close();
    setEntries([]);
    setStreamState('connecting');
    setErrorText(null);
    entryIdRef.current = 0;
    seenEventIdsRef.current = new Set();

    const source = new EventSource(streamUrl);
    sourceRef.current = source;


    source.onopen = handleOpen;
    source.onerror = handleError;
    source.addEventListener('agent_event', handleAgentEvent as EventListener);
    source.addEventListener('done', handleDone as EventListener);
    source.addEventListener('message', handleMessage as EventListener);

    return () => {
      source.close();
      if (sourceRef.current === source) sourceRef.current = null;
    };
  }, [handleAgentEvent, handleDone, handleError, handleMessage, handleOpen, streamUrl]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {errorText ? (
        <p className="shrink-0 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {errorText}
        </p>
      ) : null}

      <div className="flex-1 min-h-0 overflow-auto pr-2 pb-6">
        {entries.length ? (
          <AgentTraceEntries entries={entries} />
        ) : (
          <div className="text-sm text-slate-600">
            {streamState === 'connecting'
              ? 'Connecting…'
              : streamState === 'error'
                ? 'Stream error.'
                : 'Waiting for tool output…'}
          </div>
        )}
      </div>
    </div>
  );
}
