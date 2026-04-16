import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { API_BASE_URL } from '../../../config/env';
import { TraceOutputHoverBadge } from './TraceOutputHoverBadge';
import { ToolStatusBadge } from './ToolStatusBadge';
import { classifyToolStatus, type ToolStatus } from '../utils/status';
import { isLogThoughtTool, prettifyToolName, truncateText, tryParseJson } from '../utils/trace';
import { Badge } from '../../../shared/ui/Badge';

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

function getToolOutputValue(payload: AgentEventPayload) {
  if (payload.payload_json != null) return payload.payload_json;
  if (payload.payload_text != null) return tryParseJson(payload.payload_text);
  return null;
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
      const status = classifyToolStatus(payload.status);

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
              if (entry.kind === 'action' && entry.toolName === 'create_plan') {
                const parsedOutput = isRecord(entry.output) ? entry.output : {};
                const parsedResult = isRecord(parsedOutput.result) ? parsedOutput.result : {};
                const notes = typeof parsedResult.notes === 'string' ? parsedResult.notes : '';
                const objective =
                  typeof parsedResult.objective === 'string'
                    ? parsedResult.objective
                    : typeof parsedResult.objectives === 'string'
                      ? parsedResult.objectives
                      : '';
                const steps = Array.isArray(parsedResult.steps)
                  ? parsedResult.steps.filter((step): step is string => typeof step === 'string')
                  : [];

                return (
                  <div key={entry.id} className="space-y-1">
                    <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">PLAN</p>
                    <div className="flex flex-wrap items-center flex-row">
                      <p className="text-sm text-slate-800 font-semibold">Notes :&nbsp;</p>
                      <p className="text-sm text-slate-800">
                        {truncateText(notes, 2000)}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center flex-row">
                      <p className="text-sm text-slate-800 font-semibold">Objective :&nbsp;</p>
                      <p className="text-sm text-slate-800">
                        {truncateText(objective, 2000)}
                      </p>
                    </div>
                    <p className="text-sm font-semibold text-slate-900">Steps :</p>
                    {steps.length ? (
                      <ul className="list-disc space-y-1 pl-6 text-sm text-slate-800">
                        {steps.map((step, index) => (
                          <li key={`${entry.id}-step-${index}`}>{truncateText(step, 2000)}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-slate-500">No steps provided.</p>
                    )}
                  </div>
                );
              }

              if (entry.kind === 'thinking') {
                return (
                  <div key={entry.id} className="space-y-2">
                    <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">THINKING</p>
                    <p className="text-sm text-slate-800">{truncateText(entry.text, 2000)}</p>
                  </div>
                );
              }

              if (entry.toolName === 'log_structured_event') {
                const output = (entry.output as {
                  result: { step: string; summary: string; event_type: string; tag: string };
                }).result;
                return (
                  <div key={entry.id} className="space-y-1">
                    <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">STRUCTURED THINKING</p>
                    <p className="text-sm text-slate-900 font-semibold">
                      {prettifyToolName(output.event_type)}
                    </p>
                    <div className="flex flex-wrap items-center flex-row">
                      <p className="text-sm text-slate-800 font-semibold">Step :&nbsp;</p>
                      <p className="text-sm text-slate-800">
                        {truncateText(output.step, 2000)}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center flex-row">
                      <p className="text-sm text-slate-800 font-semibold">Summary :&nbsp;</p>
                      <p className="text-sm text-slate-800">
                        {truncateText(output.summary, 2000)}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mt-2 flex-row">
                      <p className="text-sm text-slate-800">Tag:</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge className="bg-PrimaryBlue/10 text-PrimaryBlue">
                          {prettifyToolName(output.tag)}
                        </Badge>
                        <ToolStatusBadge status={entry.status} />
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <div key={entry.id} className="space-y-2">
                  <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">ACTION</p>
                  <p className="text-sm font-semibold text-slate-900">
                    {prettifyToolName(entry.toolName)}
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <ToolStatusBadge status={entry.status} />
                    <TraceOutputHoverBadge value={entry.output} />
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
