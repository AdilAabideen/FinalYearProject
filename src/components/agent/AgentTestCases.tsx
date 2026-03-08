import { useEffect, useMemo, useRef, useState } from 'react';
import { cn } from '../../lib/cn';
import { agentTestService } from '../../services/agentTestService';
import type { AgentTestCaseRead } from '../../types/agentTests';
import { SlidingModal } from '../ui/SlidingModal';
import AgentTestRunDrawer from './AgentTestRunDrawer';

type AgentTestCasesProps = {
  agentName: string;
};

type CasesLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; cases: AgentTestCaseRead[] };

function formatCellValue(value: unknown) {
  if (value == null) return '—';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export default function AgentTestCases({ agentName }: AgentTestCasesProps) {
  const [state, setState] = useState<CasesLoadState>({ status: 'loading' });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [runBusy, setRunBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [lastRunId, setLastRunId] = useState<string | null>(null);
  const [runDrawerOpen, setRunDrawerOpen] = useState(false);
  const [lastRunCases, setLastRunCases] = useState<AgentTestCaseRead[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    async function load() {
      setSelectedIds(new Set());
      setLastRunId(null);
      setRunError(null);
      setState({ status: 'loading' });

      try {
        const cases = await agentTestService.listTestCases(
          { agentName, enabled: true, limit: 2000, offset: 0, order: 'asc' },
          ac.signal,
        );
        if (ac.signal.aborted) return;
        setState({ status: 'success', cases });
      } catch (e: unknown) {
        if (ac.signal.aborted) return;
        setState({
          status: 'error',
          message: e instanceof Error ? e.message : 'Failed to load test cases',
        });
      }
    }

    load();
    return () => ac.abort();
  }, [agentName]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const inputKeys = useMemo(() => {
    if (state.status !== 'success') return [];
    const keys = new Set<string>();
    for (const testCase of state.cases) {
      for (const key of Object.keys(testCase.inputJson)) keys.add(key);
    }
    return Array.from(keys).sort((a, b) => a.localeCompare(b));
  }, [state]);

  const outputKeys = useMemo(() => {
    if (state.status !== 'success') return [];
    const keys = new Set<string>();
    for (const testCase of state.cases) {
      for (const key of Object.keys(testCase.expectedJson)) keys.add(key);
    }
    return Array.from(keys).sort((a, b) => a.localeCompare(b));
  }, [state]);

  const selectedCount = selectedIds.size;
  const runButtonLabel = selectedCount ? `Run ${selectedCount} selected` : 'Run All';

  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleRun() {
    if (state.status !== 'success') return;
    setRunDrawerOpen(true);
    setRunError(null);
    setLastRunId(null);
    setRunBusy(true);

    const idsToRun = selectedIds.size ? Array.from(selectedIds) : state.cases.map((c) => c.id);
    const byId = new Map(state.cases.map((c) => [c.id, c]));
    setLastRunCases(
      idsToRun
        .map((id) => byId.get(id))
        .filter((c): c is AgentTestCaseRead => c != null),
    );

    try {
      const run = await agentTestService.startTestRun(agentName, idsToRun);
      setLastRunId(run.id);
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : 'Failed to start test run');
    } finally {
      setRunBusy(false);
    }
  }

  const stickySelectLeft = 'left-0';
  const stickyNameLeft = 'left-[3rem]';
  const stickyIdLeft = 'left-[19rem]';

  function stickyBodyBg(rowSelected: boolean) {
    return rowSelected ? 'bg-[#E6EFF8]' : 'bg-white group-hover:bg-slate-50';
  }

  return (
    <div className="flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Test Cases</h3>
          <p className="mt-1 text-sm text-slate-600">
            Select and run repeatable test cases for this agent.
          </p>
        </div>
      </div>

      <div className="mt-4 min-h-0 flex-1">
        {state.status === 'loading' ? (
          <p className="text-sm text-slate-600">Loading test cases…</p>
        ) : null}

        {state.status === 'error' ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {state.message}
          </div>
        ) : null}

        {state.status === 'success' ? (
          state.cases.length ? (
            <div className="flex h-full min-h-0 flex-col">
              <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
                <table className="min-w-max w-full border-separate border-spacing-0 text-xs">
                  <thead className="bg-slate-50">
                    <tr>
                      <th
                        className={cn(
                          'sticky z-30 border-b border-slate-200 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-600',
                          stickySelectLeft,
                          'w-[3rem] min-w-[3rem] bg-slate-50',
                        )}
                      >
                        Select
                      </th>
                      <th
                        className={cn(
                          'sticky z-30 border-b border-slate-200 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-600',
                          stickyNameLeft,
                          'w-[16rem] min-w-[16rem] bg-slate-50',
                        )}
                      >
                        Name
                      </th>
                      <th
                        className={cn(
                          'sticky z-30 border-b border-slate-200 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-600',
                          stickyIdLeft,
                          'w-[18rem] min-w-[18rem] bg-slate-50',
                        )}
                      >
                        ID
                      </th>

                      {inputKeys.map((key) => (
                        <th
                          key={`input-${key}`}
                          className="whitespace-nowrap border-b border-slate-200 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-600"
                        >
                          {key}
                        </th>
                      ))}

                      {outputKeys.map((key) => (
                        <th
                          key={`output-${key}`}
                          className="whitespace-nowrap border-b border-slate-200 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-600"
                        >
                          {`Output-${key}`}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {state.cases.map((testCase) => {
                      const rowSelected = selectedIds.has(testCase.id);

                      return (
                        <tr
                          key={testCase.id}
                          className={cn(
                            'group',
                            rowSelected
                              ? 'bg-[#E6EFF8] hover:bg-[#E6EFF8]'
                              : 'bg-white hover:bg-slate-50',
                          )}
                        >
                          <td
                            className={cn(
                              'sticky z-20 border-b border-slate-100 px-3 py-2',
                              stickySelectLeft,
                              'w-[3rem] min-w-[3rem]',
                              stickyBodyBg(rowSelected),
                            )}
                          >
                            <input
                              type="checkbox"
                              checked={rowSelected}
                              onChange={() => toggleSelected(testCase.id)}
                              className="h-4 w-4 rounded border-slate-300 text-PrimaryBlue focus:ring-PrimaryBlue"
                              aria-label={`Select test case ${testCase.name}`}
                            />
                          </td>
                          <td
                            className={cn(
                              'sticky z-20 border-b border-slate-100 px-3 py-2 font-semibold text-slate-900',
                              stickyNameLeft,
                              'w-[16rem] min-w-[16rem] max-w-[16rem]',
                              stickyBodyBg(rowSelected),
                            )}
                          >
                            <span className="block truncate">{testCase.name}</span>
                          </td>
                          <td
                            className={cn(
                              'sticky z-20 border-b border-slate-100 px-3 py-2 font-mono text-[11px] text-slate-700',
                              stickyIdLeft,
                              'w-[18rem] min-w-[18rem] max-w-[18rem]',
                              stickyBodyBg(rowSelected),
                            )}
                          >
                            <span className="block truncate">{testCase.id}</span>
                          </td>

                          {inputKeys.map((key) => (
                            <td
                              key={`${testCase.id}-input-${key}`}
                              className="border-b border-slate-100 px-3 py-2 align-top text-slate-700"
                            >
                              <span className="block max-w-[18rem] whitespace-pre-wrap break-words leading-snug">
                                {formatCellValue(testCase.inputJson[key])}
                              </span>
                            </td>
                          ))}

                          {outputKeys.map((key) => (
                            <td
                              key={`${testCase.id}-output-${key}`}
                              className="border-b border-slate-100 px-3 py-2 align-top text-slate-700"
                            >
                              <span className="block max-w-[18rem] whitespace-pre-wrap break-words leading-snug">
                                {formatCellValue(testCase.expectedJson[key])}
                              </span>
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 flex items-center justify-end">
                <button
                  type="button"
                  onClick={handleRun}
                  disabled={runBusy}
                  className="inline-flex items-center justify-center rounded-xl bg-PrimaryBlue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-PrimaryBlue/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {runBusy ? 'Starting…' : runButtonLabel}
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
              No enabled test cases yet.
            </div>
          )
        ) : null}
      </div>

      <SlidingModal
        open={runDrawerOpen}
        title="Test Harness"
        onClose={() => setRunDrawerOpen(false)}
        widthClassName="w-[80%]"
      >
        <AgentTestRunDrawer
          agentName={agentName}
          runId={lastRunId}
          selectedCases={lastRunCases}
          busy={runBusy}
          error={runError}
        />
      </SlidingModal>
    </div>
  );
}
