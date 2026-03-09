import { useEffect, useId, useMemo, useState } from 'react';
import type { AgentTestCaseRead } from '../../types/agentTests';
import { SegmentedTabs } from '../ui/SegmentedTabs';
import { API_BASE_URL } from '../../config/env';

type HarnessTabKey = 'cases' | 'results';
type CaseStatus = 'pending' | 'running' | 'passed' | 'failed';

const tabs: Array<{ key: HarnessTabKey; label: string }> = [
  { key: 'cases', label: 'Test Cases' },
  { key: 'results', label: 'Test Results' },
];

const friendlyLabels: Record<string, string> = {
  age_years: 'Age',
  chiefcomplaint: 'Chief Complaint',
  dbp: 'DBP',
  heartrate: 'Heart Rate',
  intime: 'Intime',
  o2sat: 'O₂ Sat',
  pain: 'Pain',
  resprate: 'Resp Rate',
  sbp: 'SBP',
  temperature: 'Temperature',
  subject_id: 'Subject ID',
};

type AgentTestRunDrawerProps = {
  agentName: string;
  runId: string | null;
  selectedCases: AgentTestCaseRead[];
  busy: boolean;
  error: string | null;
  onStart: () => void | Promise<void>;
};

function CaseBadge({ label, value }: { label: string; value: string | number }) {
  const display = friendlyLabels[label] ?? label;
  return (
    <span className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-700">
      {display}: {value}
    </span>
  );
}

function StatusDot({ status }: { status: CaseStatus }) {
  if (status === 'running') {
    return (
      <span className="inline-flex h-4 w-4 items-center justify-center">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-PrimaryBlue" />
      </span>
    );
  }
  if (status === 'failed') return <span className="text-xs font-semibold text-rose-600">×</span>;
  if (status === 'passed') return <span className="text-xs font-semibold text-emerald-600">✓</span>;
  return <span className="inline-flex h-2 w-2 rounded-full bg-slate-300" />;
}

function titleCase(value: string) {
  return value.replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AgentTestRunDrawer({
  agentName,
  runId,
  selectedCases,
  busy,
  error,
  onStart,
}: AgentTestRunDrawerProps) {
  const baseId = useId();
  const [activeTab, setActiveTab] = useState<HarnessTabKey>('results');
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [caseStates, setCaseStates] = useState<Record<string, { status: CaseStatus; agentRunId?: string }>>({});
  const [classification, setClassification] = useState<string | null>(null);

  const totals = useMemo(() => {
    const total = selectedCases.length;
    const completed = Object.values(caseStates).filter(
      (c) => c.status === 'passed' || c.status === 'failed',
    ).length;
    const running = Object.values(caseStates).filter((c) => c.status === 'running').length;
    return { total, completed, running, queued: Math.max(total - completed - running, 0) };
  }, [caseStates, selectedCases.length]);

  useEffect(() => {
    function resetSelection() {
      const initial: Record<string, { status: CaseStatus }> = {};
      for (const c of selectedCases) initial[c.id] = { status: 'pending' };
      setCaseStates(initial);
      setActiveCaseId(selectedCases[0]?.id ?? null);
      setClassification(null);
    }
    resetSelection();
  }, [selectedCases]);

  useEffect(() => {
    if (!runId) return undefined;
    const url = `${API_BASE_URL}/api/tests/runs/${encodeURIComponent(runId)}/stream`;
    const source = new EventSource(url);

    source.addEventListener('case_start', (evt) => {
      try {
        const payload = JSON.parse((evt as MessageEvent<string>).data) as { test_case_id?: string };
        const testCaseId = payload.test_case_id;
        if (!testCaseId) return;
        setCaseStates((prev) => ({
          ...prev,
          [testCaseId]: { ...(prev[testCaseId] ?? { status: 'pending' }), status: 'running', testCaseId },
        }));
        setActiveCaseId((current) => current ?? testCaseId);
      } catch {
        // ignore
      }
    });

    source.addEventListener('case_done', (evt) => {
      try {
        const payload = JSON.parse((evt as MessageEvent<string>).data) as {
          test_case_id?: string;
          passed?: boolean;
          status?: string;
        };
        const caseId = payload.test_case_id;
        if (!caseId) return;
        const passed =
          typeof payload.passed === 'boolean'
            ? payload.passed
            : (payload.status ?? '').toLowerCase().includes('pass');
        setCaseStates((prev) => ({
          ...prev,
          [caseId]: { ...(prev[caseId] ?? { status: 'pending' }), status: passed ? 'passed' : 'failed' },
        }));
      } catch {
        // ignore
      }
    });

    source.addEventListener('run_done', (evt) => {
      try {
        const payload = JSON.parse((evt as MessageEvent<string>).data) as {
          metrics?: { classification?: string };
        };
        console.log('payload', payload);
        if (payload.metrics?.classification) setClassification(String(payload.metrics.classification));
      } catch {
        // ignore
      }
    });

    source.addEventListener('done', () => source.close());
    source.onerror = () => source.close();
    return () => source.close();
  }, [runId]);

  const activeCase = useMemo(
    () => selectedCases.find((c) => c.id === activeCaseId),
    [selectedCases, activeCaseId],
  );

  function tabId(key: HarnessTabKey) {
    return `${baseId}-tab-${key}`;
  }

  function panelId(key: HarnessTabKey) {
    return `${baseId}-panel-${key}`;
  }

  return (
    <div className="flex min-h-0 flex-col gap-4 h-full overflow-y-hidden">
      <SegmentedTabs
        idBase={baseId}
        tabs={tabs}
        value={activeTab}
        onChange={setActiveTab}
        ariaLabel="Test harness tabs"
        className="max-w-sm"
      />
      <span className="sr-only">{agentName}</span>

      <div
        id={panelId('cases')}
        role="tabpanel"
        aria-labelledby={tabId('cases')}
        hidden={activeTab !== 'cases'}
        className="h-full"
      >
        <div className="grid h-full grid-cols-5 grid-rows-8 rounded-2xl border border-slate-200 bg-white overflow-y-hidden">
          <div className="col-span-3 row-span-8 min-h-0 overflow-auto border-r border-slate-200 pb-6">
            {selectedCases.length ? (
              <div className="divide-y divide-slate-200">
                {selectedCases.map((testCase) => {
                  const status = caseStates[testCase.id]?.status ?? 'pending';
                  const isActive = activeCaseId === testCase.id;
                  return (
                    <button
                      key={testCase.id}
                      type="button"
                      onClick={() => setActiveCaseId(testCase.id)}
                      className={`flex w-full items-center justify-between p-4 text-left transition ${
                        isActive ? 'bg-slate-50' : 'hover:bg-slate-50'
                      }`}
                    >
                      <div className="min-w-0 space-y-1">
                        <p className="truncate text-sm font-semibold text-slate-900">
                          {titleCase(testCase.name)}
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(testCase.inputJson).map(([label, value]) => (
                            <CaseBadge key={label} label={label} value={value as string | number} />
                          ))}
                        </div>
                      </div>
                      <div className="shrink-0">
                        <StatusDot status={status} />
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="p-4 text-xs text-slate-500">No cases selected.</p>
            )}
          </div>

          <div className="col-span-2 row-span-2 border-b border-slate-200  px-6 py-4 text-slate-900">
            <div className="flex flex-wrap items-center justify-between gap-6">
              <div>
                <p className="text-[11px] uppercase tracking-[0.3em] text-slate-900/70">Harness panel</p>
                <h3 className="text-2xl font-semibold">Start Test Run</h3>
                <p className="text-sm text-slate-900/70">
                  {selectedCases.length} case{selectedCases.length === 1 ? '' : 's'} selected
                </p>
              </div>
              <button
                type="button"
                onClick={onStart}
                disabled={busy || !selectedCases.length}
                className=" cursor-pointer hover:scale-[1.02] transition-all duration-300 inline-flex items-center gap-2 rounded-2xl bg-PrimaryBlue px-5 py-2 text-xs font-semibold text-white shadow-slate-900/40 backdrop-blur  hover:bg-PrimaryBlue/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span>{busy ? 'Starting…' : 'Start'}</span>
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
              </button>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-4">
              {[
                { label: 'Total cases', value: totals.total },
                { label: 'Running', value: totals.running },
                { label: 'Completed', value: totals.completed },
                { label: 'Queued', value: totals.queued },
                ...(classification ? [{ label: 'Classification', value: classification }] : []),
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-2xl border border-slate-200 bg-white/5 p-3 text-[10px] uppercase tracking-wide text-slate-900/80 backdrop-blur"
                >
                  <p className="text-[10px] font-semibold text-slate-900/60">{stat.label}</p>
                  <p className="text-xl font-semibold">{stat.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-2 row-span-6 min-h-0 overflow-hidden p-4">
            <div className="grid h-full grid-rows-[1fr_1fr_1fr] gap-4">
              <div className="rounded-xl row-span-1 border border-slate-200 bg-white p-3">
                <p className="text-xs font-semibold text-slate-900">Case details</p>
                {activeCase ? (
                  <div className="mt-2 space-y-2">
                    <p className="text-sm font-semibold text-slate-900">{titleCase(activeCase.name)}</p>
                    <p className="font-mono text-[11px] text-slate-500">{activeCase.id}</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(activeCase.inputJson).map(([label, value]) => (
                        <CaseBadge key={label} label={label} value={value as string | number} />
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-600">Select a test case to view details.</p>
                )}
              </div>

              <div className="row-span-2 rounded-xl border border-slate-200 bg-white p-3">
                <p className="text-xs font-semibold text-slate-900">Test traces</p>
                <div className="mt-2 min-h-0 h-[92%] overflow-hidden rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <p className="text-xs text-slate-600">
                    Traces hidden for now. Run will still execute.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        id={panelId('results')}
        role="tabpanel"
        aria-labelledby={tabId('results')}
        hidden={activeTab !== 'results'}
      >
        {busy ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Starting test run…
          </div>
        ) : null}

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {runId ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Started test run <span className="font-mono text-xs font-semibold text-slate-900">{runId}</span>
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
            Results will appear here.
          </div>
        )}
      </div>
    </div>
  );
}
