import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { agentRunService } from '../../../services/agentRunService';
import type { AgentRunRead } from '../../../types/agentRuns';
import { AgentRunReview } from './AgentRunReview';
import { Badge } from '../../../shared/ui/Badge';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { IoIosRefresh } from 'react-icons/io';
import { RunStatusBadge } from './RunStatusBadge';

type PreviousRunsProps = {
  agentName: string;
};

type RunsLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; runs: AgentRunRead[] };

// Formats timestamp.
function formatTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    date,
  );
}

// Renders the previous runs.
export default function PreviousRuns({ agentName }: PreviousRunsProps) {
  const [state, setState] = useState<RunsLoadState>({ status: 'loading' });
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchRuns = useCallback(
    (signal: AbortSignal) =>
      agentRunService.listAgentRuns({ agentName, limit: 50, offset: 0, order: 'desc' }, signal),
    [agentName],
  );

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    async function load() {
      setState({ status: 'loading' });
      try {
        const runs = await fetchRuns(ac.signal);
        if (ac.signal.aborted) return;
        setState({ status: 'success', runs });
      } catch (e: unknown) {
        if (ac.signal.aborted) return;
        setState({
          status: 'error',
          message: e instanceof Error ? e.message : 'Failed to load runs',
        });
      }
    }

    load();

    return () => ac.abort();
  }, [fetchRuns]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const headerSuffix = useMemo(() => {
    if (state.status !== 'success') return null;
    return `${state.runs.length} run${state.runs.length === 1 ? '' : 's'}`;
  }, [state]);

// Handles refresh.
  function handleRefresh() {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    async function load() {
      setState({ status: 'loading' });
      try {
        const runs = await fetchRuns(ac.signal);
        if (ac.signal.aborted) return;
        setState({ status: 'success', runs });
      } catch (e: unknown) {
        if (ac.signal.aborted) return;
        setState({
          status: 'error',
          message: e instanceof Error ? e.message : 'Failed to load runs',
        });
      }
    }

    load();
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      {selectedRunId ? (
        <AgentRunReview runId={selectedRunId} onBack={() => setSelectedRunId(null)} />
      ) : (
        <>
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Previous Runs</h3>
              <p className="mt-1 text-sm text-slate-600">Review prior agent runs and outputs.</p>
            </div>
            <div className="flex items-center gap-2">
              {headerSuffix ? (
                <Badge className="shrink-0 bg-slate-100 text-slate-700 ring-slate-200">
                  {headerSuffix}
                </Badge>
              ) : null}
              <button type="button" onClick={handleRefresh}>
                <Badge className="flex items-center gap-1 shrink-0 bg-PrimaryBlue/10 text-PrimaryBlue ring-PrimaryBlue/20 cursor-pointer transition-all duration-300 hover:scale-[1.01]">
                  <IoIosRefresh className="size-4 mb-[2px]" />
                  <span className="mt-[2px]">Refresh</span>
                </Badge>
              </button>
            </div>
          </div>

          <div className="mt-4 min-h-0 flex-1">
            {state.status === 'loading' ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }, (_, i) => (
                  <div
                    key={i}
                    className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
                      <div className="h-6 w-20 animate-pulse rounded-full bg-slate-200" />
                    </div>
                    <div className="mt-3 h-3 w-56 animate-pulse rounded bg-slate-100" />
                    <div className="mt-2 h-3 w-40 animate-pulse rounded bg-slate-100" />
                  </div>
                ))}
              </div>
            ) : null}

            {state.status === 'error' ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                {state.message}
              </div>
            ) : null}

            {state.status === 'success' ? (
              state.runs.length ? (
                <div className="space-y-3">
                  {state.runs.map((run) => (
                    <article
                      key={run.id}
                      className="rounded-2xl border border-slate-200 bg-white p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-900">
                            Run{' '}
                            <span className="font-mono text-xs font-semibold text-slate-700">
                              {run.id}
                            </span>
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            Created {formatTimestamp(run.createdAt)}
                            {run.modelName ? <span className="text-slate-400"> · </span> : null}
                            {run.modelName ? (
                              <span className="text-slate-600">{run.modelName}</span>
                            ) : null}
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setSelectedRunId(run.id)}
                            className="inline-flex items-center rounded-full bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700 ring-1 ring-sky-200 transition hover:bg-sky-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                          >
                            View Traces
                          </button>
                          <RunStatusBadge status={run.status} className="shrink-0" />
                        </div>
                      </div>

                      {run.errorText ? (
                        <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                          {run.errorText}
                        </div>
                      ) : null}

                      <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                        <summary className="cursor-pointer select-none text-xs font-semibold text-slate-700">
                          Inspect
                        </summary>
                        <div className="mt-3 grid gap-3 lg:grid-cols-2">
                          <div className="min-w-0">
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                              Parameters
                            </p>
                            <div className="mt-2 max-h-[min(18rem,40vh)] overflow-y-auto overflow-x-hidden rounded-2xl border border-slate-200 bg-white p-3">
                              <JsonInspector value={run.inputJson} />
                            </div>
                          </div>

                          <div className="min-w-0">
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                              Output
                            </p>
                            {run.outputJson ? (
                              <div className="mt-2 max-h-[min(18rem,40vh)] overflow-y-auto overflow-x-hidden rounded-2xl border border-slate-200 bg-white p-3">
                                <JsonInspector value={run.outputJson} />
                              </div>
                            ) : (
                              <div className="mt-2 rounded-2xl border border-slate-200 bg-white p-3 text-xs text-slate-500">
                                No output yet.
                              </div>
                            )}
                          </div>
                        </div>
                      </details>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 text-sm text-slate-600">
                  No previous runs yet.
                </div>
              )
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}
