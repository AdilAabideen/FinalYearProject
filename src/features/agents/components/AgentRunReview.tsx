import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { agentEventService } from '../../../services/agentEventService';
import { agentRunService } from '../../../services/agentRunService';
import type { AgentEventRead } from '../../../types/agentEvents';
import type { AgentRunRead } from '../../../types/agentRuns';
import { SegmentedTabs } from '../../../shared/ui/SegmentedTabs';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { RunStatusBadge } from './RunStatusBadge';
import { ToolStatusBadge } from './ToolStatusBadge';
import { TraceOutputHoverBadge } from './TraceOutputHoverBadge';
import { classifyToolStatus, type ToolStatus } from '../utils/status';
import { prettifyToolName, truncateText, tryParseJson } from '../utils/trace';

type OutputTabKey = 'traces' | 'results';

const outputTabs: Array<{ key: OutputTabKey; label: string }> = [
  { key: 'traces', label: 'Agent Traces' },
  { key: 'results', label: 'Results' },
];

type TraceEntry =
  | { id: string; kind: 'thinking'; text: string }
  | { id: string; kind: 'action'; toolName: string; status: ToolStatus; output: unknown }
  | {
      id: string;
      kind: 'event';
      eventType: string;
      title: string;
      status: ToolStatus;
      payload: unknown;
    };

type AgentRunReviewProps = {
  runId: string;
  onBack: () => void;
};

type LoadState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; value: T };

function getEventPayload(event: AgentEventRead): unknown {
  if (event.payloadJson != null) return event.payloadJson;
  if (event.payloadText != null) return tryParseJson(event.payloadText);
  return null;
}

async function loadAllEvents(runId: string, signal: AbortSignal) {
  const items: AgentEventRead[] = [];
  let afterSeq = 0;
  let guard = 0;

  while (!signal.aborted && guard < 100) {
    guard += 1;
    const page = await agentEventService.listAgentEvents(runId, { afterSeq, limit: 1000 }, signal);
    if (!page.events.length) break;
    items.push(...page.events);
    if (page.nextAfterSeq <= afterSeq) break;
    afterSeq = page.nextAfterSeq;
  }

  return items;
}

function toTraceEntries(events: AgentEventRead[]): TraceEntry[] {
  return events.map((event) => {
    const payload = getEventPayload(event);
    const id = String(event.id);
    const toolName = event.toolName ?? '';

    if (event.eventType === 'thought' && typeof event.payloadText === 'string') {
      return { id, kind: 'thinking', text: event.payloadText };
    }

    if (event.eventType === 'tool_result' && toolName) {
      return {
        id,
        kind: 'action',
        toolName,
        status: classifyToolStatus(event.status),
        output: payload,
      };
    }

    const title = toolName
      ? prettifyToolName(toolName)
      : event.nodeName
        ? event.nodeName
        : event.eventType;

    return {
      id,
      kind: 'event',
      eventType: event.eventType,
      title,
      status: classifyToolStatus(event.status),
      payload,
    };
  });
}

export function AgentRunReview({ runId, onBack }: AgentRunReviewProps) {
  const outputTabsId = useId();
  const [view, setView] = useState<'input' | 'output'>('output');
  const [activeOutputTab, setActiveOutputTab] = useState<OutputTabKey>('traces');
  const [runState, setRunState] = useState<LoadState<AgentRunRead>>({ status: 'loading' });
  const [eventsState, setEventsState] = useState<LoadState<AgentEventRead[]>>({
    status: 'loading',
  });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    async function load() {
      setRunState({ status: 'loading' });
      setEventsState({ status: 'loading' });

      try {
        const run = await agentRunService.getAgentRun(runId, ac.signal);
        if (ac.signal.aborted) return;
        setRunState({ status: 'success', value: run });
      } catch (e: unknown) {
        if (ac.signal.aborted) return;
        setRunState({
          status: 'error',
          message: e instanceof Error ? e.message : 'Failed to load run',
        });
      }

      try {
        const events = await loadAllEvents(runId, ac.signal);
        if (ac.signal.aborted) return;
        setEventsState({ status: 'success', value: events });
      } catch (e: unknown) {
        if (ac.signal.aborted) return;
        setEventsState({
          status: 'error',
          message: e instanceof Error ? e.message : 'Failed to load events',
        });
      }
    }

    load();

    return () => ac.abort();
  }, [runId]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const traceEntries = useMemo(() => {
    if (eventsState.status !== 'success') return [];
    return toTraceEntries(eventsState.value);
  }, [eventsState]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 pt-3 h-full flex min-h-0 flex-col">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-slate-900">Run Review</h3>
          <p className="mt-1 text-sm text-slate-600">
            View traces, results, and the original inputs for this run.
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
          >
            Back to runs
          </button>
          <button
            type="button"
            onClick={() => setView((prev) => (prev === 'output' ? 'input' : 'output'))}
            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
          >
            {view === 'output' ? 'Back to inputs' : 'Back to traces'}
          </button>
        </div>
      </div>

      <div className="mt-3 text-xs font-semibold text-slate-500">
        Run ID: <span className="font-mono text-slate-700">{runId}</span>
        {runState.status === 'success' ? (
          <RunStatusBadge status={runState.value.status} className="ml-2" />
        ) : null}
      </div>

      {view === 'input' ? (
        <div className="mt-4 flex-1 min-h-0 overflow-auto">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <h4 className="text-sm font-semibold text-slate-900">Inputs</h4>
            {runState.status === 'loading' ? (
              <p className="mt-2 text-sm text-slate-600">Loading inputs…</p>
            ) : runState.status === 'error' ? (
              <p className="mt-2 text-sm text-rose-700">{runState.message}</p>
            ) : (
              <div className="mt-3 max-h-[min(30rem,65vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                <JsonInspector value={runState.value.inputJson} />
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="mt-4 flex-1 min-h-0 flex flex-col">
          <SegmentedTabs
            idBase={outputTabsId}
            tabs={outputTabs}
            value={activeOutputTab}
            onChange={setActiveOutputTab}
            ariaLabel="Run review output views"
          />

          <div className="mt-4 flex-1 min-h-0">
            <div
              id={`${outputTabsId}-panel-traces`}
              role="tabpanel"
              aria-labelledby={`${outputTabsId}-tab-traces`}
              hidden={activeOutputTab !== 'traces'}
              className="h-full min-h-0 overflow-auto pr-2"
            >
              {eventsState.status === 'loading' ? (
                <p className="text-sm text-slate-600">Loading traces…</p>
              ) : eventsState.status === 'error' ? (
                <p className="text-sm text-rose-700">{eventsState.message}</p>
              ) : traceEntries.length ? (
                <div className="space-y-8 py-1">
                  {traceEntries.map((entry) => {
                    if (entry.kind === 'thinking') {
                      return (
                        <div key={entry.id} className="space-y-2">
                          <p className="text-xs font-semibold tracking-wide text-slate-900">THINKING</p>
                          <p className="text-sm text-slate-800">{truncateText(entry.text, 2000)}</p>
                        </div>
                      );
                    }

                    if (entry.kind === 'action') {
                      return (
                        <div key={entry.id} className="space-y-2">
                          <p className="text-xs font-semibold tracking-wide text-slate-900">ACTION</p>
                          <p className="text-sm font-semibold text-PrimaryBlue">
                            {prettifyToolName(entry.toolName)}
                          </p>
                          <div className="flex flex-wrap items-center gap-2">
                            <ToolStatusBadge status={entry.status} />
                            <TraceOutputHoverBadge value={entry.output} />
                          </div>
                        </div>
                      );
                    }

                    
                  })}
                </div>
              ) : (
                <p className="text-sm text-slate-600">No trace events yet.</p>
              )}
            </div>

            <div
              id={`${outputTabsId}-panel-results`}
              role="tabpanel"
              aria-labelledby={`${outputTabsId}-tab-results`}
              hidden={activeOutputTab !== 'results'}
              className="h-full min-h-0 overflow-auto"
            >
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <h4 className="text-sm font-semibold text-slate-900">Results</h4>
                {runState.status === 'loading' ? (
                  <p className="mt-2 text-sm text-slate-600">Loading results…</p>
                ) : runState.status === 'error' ? (
                  <p className="mt-2 text-sm text-rose-700">{runState.message}</p>
                ) : runState.value.errorText ? (
                  <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                    {runState.value.errorText}
                  </div>
                ) : runState.value.outputJson ? (
                  <div className="mt-3 max-h-[min(28rem,60vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <JsonInspector value={runState.value.outputJson} />
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-600">No output yet.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
