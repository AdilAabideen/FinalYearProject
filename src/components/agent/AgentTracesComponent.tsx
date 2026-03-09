import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { API_BASE_URL } from '../../config/env';
import { JsonInspector } from '../ui/JsonInspector';

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

type ToolStatus = 'succeeded' | 'error' | 'unknown';

type TraceEntry =
  | {
      id: string;
      kind: 'thinking';
      text: string;
    }
  | {
      id: string;
      kind: 'action';
      toolName: string;
      status: ToolStatus;
      output: unknown;
    };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

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

function isLogThoughtTool(toolName: string) {
  const normalized = toolName.toLowerCase().replace(/[\s_-]+/g, '');
  return normalized.includes('logthought');
}

function truncateText(value: string, max: number) {
  if (value.length <= max) return value;
  return `${value.slice(0, max)}…`;
}

function prettifyToolName(toolName: string) {
  return toolName
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function classifyStatus(status: string | undefined): ToolStatus {
  if (!status) return 'unknown';
  const normalized = status.toLowerCase();
  if (
    normalized.includes('succeed') ||
    normalized.includes('success') ||
    normalized.includes('complete') ||
    normalized.includes('done')
  ) {
    return 'succeeded';
  }
  if (normalized.includes('error') || normalized.includes('fail')) return 'error';
  return 'unknown';
}

function tryParseJson(value: string) {
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}

function getToolOutputValue(payload: AgentEventPayload) {
  if (payload.payload_json != null) return payload.payload_json;
  if (payload.payload_text != null) return tryParseJson(payload.payload_text);
  return null;
}

function StatusBadge({ status }: { status: ToolStatus }) {
  const label = status === 'succeeded' ? 'succeeded' : status === 'error' ? 'error' : 'unknown';
  const className =
    status === 'succeeded'
      ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
      : status === 'error'
        ? 'bg-rose-50 text-rose-700 ring-rose-200'
        : 'bg-slate-100 text-slate-700 ring-slate-200';

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${className}`}
    >
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

function OutputHoverBadge({ value }: { value: unknown }) {
  const hasValue =
    value != null && (typeof value !== 'string' || value.trim().length > 0);

  return (
    <span className="group relative inline-flex ">
      <span className="inline-flex cursor-default items-center rounded-full bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700 ring-1 ring-sky-200">
        Output
      </span>

      <div className="absolute left-0 top-full z-20 mt-2 hidden w-140 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl group-hover:block group-focus-within:block">
        {hasValue ? (
          <div className="max-h-80 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <JsonInspector value={value} />
          </div>
        ) : (
          <p className="text-xs text-slate-500">No output.</p>
        )}
      </div>
    </span>
  );
}

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

  const handleOpen = useCallback(() => {
    setStreamState('open');
    setErrorText(null);
  }, []);

  const handleError = useCallback(() => {
    setStreamState('error');
    setErrorText('Stream error (check server logs / CORS).');
  }, []);

  const handleMessage = useCallback((event: MessageEvent<string>) => {
    void event;
  }, []);

  const handleDone = useCallback((event: MessageEvent<string>) => {
    void event;
    setStreamState('done');
    sourceRef.current?.close();
    onDoneRef.current?.(runId);
  }, [runId]);

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
      const status = classifyStatus(payload.status);

      const hasOutput = output != null && (typeof output !== 'string' || output.trim().length > 0);

      entryIdRef.current += 1;
      const idSuffix = event.lastEventId ? `${event.lastEventId}` : `evt-${Date.now()}`;
      const entryId = `${idSuffix}-${entryIdRef.current}`;

      if (payload.event_type === 'thought' || isLogThoughtTool(payload.tool_name)) {
        const text = payload.payload_text?.trim();
        if (!text) return;
        setEntries((prev) => [...prev, { id: entryId, kind: 'thinking', text }]);
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
      // Ignore malformed agent_event payloads.
    }
  }, []);

  useEffect(() => {
    sourceRef.current?.close();
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
          <div className="space-y-8 py-1">
            {entries.map((entry) => {
              if (entry.kind === 'thinking') {
                return (
                  <div key={entry.id} className="space-y-2">
                    <p className="text-xs font-semibold tracking-wide text-slate-900">THINKING</p>
                    <p className="text-sm text-slate-800">{truncateText(entry.text, 2000)}</p>
                  </div>
                );
              }

              return (
                <div key={entry.id} className="space-y-2">
                  <p className="text-xs font-semibold tracking-wide text-slate-900">ACTION</p>
                  <p className="text-sm font-semibold text-PrimaryBlue">
                    {prettifyToolName(entry.toolName)}
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={entry.status} />
                    <OutputHoverBadge value={entry.output} />
                  </div>
                </div>
              );
            })}
          </div>
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
