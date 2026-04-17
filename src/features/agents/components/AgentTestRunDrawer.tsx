import { useCallback, useEffect, useId, useMemo, useState } from 'react';
import type { AgentTestCaseRead } from '../../../types/agentTests';
import { API_BASE_URL } from '../../../config/env';
import { agentRunService } from '../../../services/agentRunService';
import { AgentTracesComponent } from './AgentTracesComponent';
import { SegmentedTabs } from '../../../shared/ui/SegmentedTabs';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { useModels } from '../hooks/useModels';

type HarnessTabKey = 'cases' | 'results';
type ViewerTabKey = 'case_details' | 'test_traces' | 'outputs';
type CaseStatus = 'pending' | 'running' | 'passed' | 'failed';
type RunPhase = 'idle' | 'running' | 'done';

type RunMetrics = {
  total?: number;
  passed?: number;
  failed?: number;
  exec_failed?: number;
  invalid_pred?: number;
  pass_rate?: number;
  classification?: {
    label?: string;
    tp?: number;
    tn?: number;
    fp?: number;
    fn?: number;
    n_eval?: number;
    accuracy?: number;
    precision?: number | null;
    recall?: number | null;
    f1?: number | null;
    specificity?: number | null;
    excluded?: {
      exec_failed?: number;
      invalid_pred?: number;
      other?: number;
    };
  };
};

type CaseOutputState = {
  status: 'idle' | 'loading' | 'ready' | 'error';
  agentRunId?: string;
  output?: Record<string, unknown> | null;
  error?: string;
};

const harnessTabs: Array<{ key: HarnessTabKey; label: string }> = [
  { key: 'cases', label: 'Test Cases' },
  { key: 'results', label: 'Test Results' },
];

const viewerTabs: Array<{ key: ViewerTabKey; label: string }> = [
  { key: 'case_details', label: 'Case Details' },
  { key: 'test_traces', label: 'Test Traces' },
  { key: 'outputs', label: 'Outputs' },
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
  onStart: (modelId?: string) => void | Promise<void>;
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
  const color =
    status === 'running'
      ? 'bg-orange-400'
      : status === 'passed'
        ? 'bg-emerald-500'
        : status === 'failed'
          ? 'bg-rose-500'
          : 'bg-slate-300';
  return <span className={`inline-flex h-2.5 w-2.5 rounded-full ${color}`} />;
}

function titleCase(value: string) {
  return value.replace(/\b\w/g, (c) => c.toUpperCase());
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

function extractCaseId(payload: Record<string, unknown>) {
  return (
    asString(payload.test_case_id) ??
    asString(payload.case_id) ??
    (isRecord(payload.result)
      ? asString(payload.result.test_case_id) ?? asString(payload.result.case_id)
      : undefined) ??
    (isRecord(payload.payload_json)
      ? asString(payload.payload_json.test_case_id) ?? asString(payload.payload_json.case_id)
      : undefined)
  );
}

function extractAgentRunId(payload: Record<string, unknown>) {
  return (
    asString(payload.agent_run_id) ??
    asString(payload.run_id) ??
    (isRecord(payload.result)
      ? asString(payload.result.agent_run_id) ?? asString(payload.result.run_id)
      : undefined) ??
    (isRecord(payload.payload_json)
      ? asString(payload.payload_json.agent_run_id) ?? asString(payload.payload_json.run_id)
      : undefined)
  );
}

function extractPassed(payload: Record<string, unknown>) {
  if (typeof payload.passed === 'boolean') return payload.passed;
  const status =
    asString(payload.status) ??
    (isRecord(payload.result) ? asString(payload.result.status) : undefined) ??
    (isRecord(payload.payload_json) ? asString(payload.payload_json.status) : undefined) ??
    '';
  return status.toLowerCase().includes('pass');
}

function extractMetrics(payload: Record<string, unknown>) {
  if (isRecord(payload.metrics)) return payload.metrics as RunMetrics;
  if (isRecord(payload.metrics_json)) return payload.metrics_json as RunMetrics;
  if (isRecord(payload.result) && isRecord(payload.result.metrics)) return payload.result.metrics as RunMetrics;
  return null;
}

export default function AgentTestRunDrawer({
  agentName,
  runId,
  selectedCases,
  error,
  onStart,
}: AgentTestRunDrawerProps) {
  const harnessTabsId = useId();
  const viewerTabsId = useId();
  const modelSelectId = useId();
  const [activeHarnessTab, setActiveHarnessTab] = useState<HarnessTabKey>('cases');
  const [activeViewerTab, setActiveViewerTab] = useState<ViewerTabKey>('case_details');
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [caseStates, setCaseStates] = useState<Record<string, { status: CaseStatus }>>({});
  const [runMetrics, setRunMetrics] = useState<RunMetrics | null>(null);
  const [runPhase, setRunPhase] = useState<RunPhase>('idle');
  const [agentRunByCaseId, setAgentRunByCaseId] = useState<Record<string, string>>({});
  const [outputsByCaseId, setOutputsByCaseId] = useState<Record<string, CaseOutputState>>({});
  const { models, status: modelsStatus, selectedModelId, setSelectedModelId } = useModels();

  const totals = useMemo(() => {
    const total = selectedCases.length;
    const completed = Object.values(caseStates).filter(
      (c) => c.status === 'passed' || c.status === 'failed',
    ).length;
    const running = Object.values(caseStates).filter((c) => c.status === 'running').length;
    return { total, completed, running, queued: Math.max(total - completed - running, 0) };
  }, [caseStates, selectedCases.length]);

  const fetchCaseOutput = useCallback(
    async (caseId: string, agentRunId: string) => {
      if (!agentRunId || !caseId) return;

      try {
        const run = await agentRunService.getAgentRun(agentRunId);
        setOutputsByCaseId((prev) => {
          return {
            ...prev,
            [caseId]: {
              status: 'ready',
              agentRunId,
              output: run.outputJson ?? null,
            },
          };
        });
      }
      catch(e: unknown) {
        setOutputsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'error',
            agentRunId,
            error: e instanceof Error ? e.message : 'Failed to load output',
          },
        }));
      }
    },
    [],
  );

  useEffect(() => {
    const initial: Record<string, { status: CaseStatus }> = {};
    for (const c of selectedCases) initial[c.id] = { status: 'pending' };
    setCaseStates(initial);
    setActiveCaseId(selectedCases[0]?.id ?? null);
    setRunMetrics(null);
    setRunPhase(runId ? 'running' : 'idle');
    setAgentRunByCaseId({});
    setOutputsByCaseId({});
    setActiveViewerTab('case_details');
    setActiveHarnessTab('cases');
  }, [selectedCases, runId]);

  useEffect(() => {
    if (!runId) return undefined;

    const caseRunMap: Record<string, string> = {};
    const url = `${API_BASE_URL}/api/tests/runs/${encodeURIComponent(runId)}/stream`;
    const source = new EventSource(url);
    setRunPhase('running');

    const handleCaseStartPayload = (payload: Record<string, unknown>) => {
      const caseId = extractCaseId(payload);
      const agentRunId = extractAgentRunId(payload);
      if (!caseId || !agentRunId) return;

      caseRunMap[caseId] = agentRunId;
      setAgentRunByCaseId((prev) => ({ ...prev, [caseId]: agentRunId }));
      setCaseStates((prev) => ({
        ...prev,
        [caseId]: { ...(prev[caseId] ?? { status: 'pending' }), status: 'running' },
      }));
      setOutputsByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: prev[caseId]?.status === 'ready' ? 'ready' : 'idle',
          agentRunId,
          output: prev[caseId]?.output,
          error: prev[caseId]?.error,
        },
      }));
      setActiveCaseId((current) => current ?? caseId);
    };

    const handleCaseDonePayload = (payload: Record<string, unknown>) => {
      const caseId = extractCaseId(payload);
      if (!caseId) return;

      const passed = extractPassed(payload);
      setCaseStates((prev) => ({
        ...prev,
        [caseId]: {
          ...(prev[caseId] ?? { status: 'pending' }),
          status: passed ? 'passed' : 'failed',
        },
      }));

      const agentRunId = extractAgentRunId(payload) ?? caseRunMap[caseId];
      if (!agentRunId) {
        setOutputsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'error',
            error: 'Agent run id not available for this test case.',
          },
        }));
        return;
      }

      caseRunMap[caseId] = agentRunId;
      setAgentRunByCaseId((prev) => ({ ...prev, [caseId]: agentRunId }));
      void fetchCaseOutput(caseId, agentRunId);
    };

    const handleRunDonePayload = (payload: Record<string, unknown>) => {
      const metrics = extractMetrics(payload);
      if (metrics) setRunMetrics(metrics);
      setRunPhase('done');
    };

    const parseEventPayload = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as unknown;
        return isRecord(parsed) ? parsed : null;
      } catch {
        return null;
      }
    };

    source.addEventListener('case_start', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      if (!payload) return;
      handleCaseStartPayload(payload);
    });

    source.addEventListener('case_done', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      console.log("Done Payload", payload);
      if (!payload) return;
      handleCaseDonePayload(payload);
    });

    source.addEventListener('run_done', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      if (!payload) return;
      handleRunDonePayload(payload);
    });

    // Some servers emit only generic messages with an "event_type" field.
    source.addEventListener('message', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      console.log("Message Payload", payload);
      if (!payload) return;

      const eventType =
        asString(payload.event_type) ??
        (isRecord(payload.result) ? asString(payload.result.event_type) : undefined) ??
        (isRecord(payload.payload_json) ? asString(payload.payload_json.event_type) : undefined);

      if (eventType === 'case_start') handleCaseStartPayload(payload);
      if (eventType === 'case_done') handleCaseDonePayload(payload);
      if (eventType === 'run_done') handleRunDonePayload(payload);
      console.log("Event Type", eventType);
    });

    source.addEventListener('done', () => {
      console.log("Done Event");
      setRunPhase('done');
      source.close();
    });

    // Keep native EventSource retry behavior; mark state for visibility.
    source.onerror = () => {
      console.log("Error Event");
      setRunPhase((prev) => (prev === 'running' ? 'running' : prev));
    };

    return () => {
      source.close();
    };
  }, [runId, fetchCaseOutput]);

  const activeCase = useMemo(
    () => selectedCases.find((c) => c.id === activeCaseId),
    [selectedCases, activeCaseId],
  );

  const activeAgentRunId = activeCaseId ? agentRunByCaseId[activeCaseId] ?? null : null;
  const activeOutputState = activeCaseId ? outputsByCaseId[activeCaseId] : undefined;
  const activeCaseStatus = activeCaseId ? caseStates[activeCaseId]?.status : undefined;

  function harnessTabId(key: HarnessTabKey) {
    return `${harnessTabsId}-tab-${key}`;
  }

  function harnessPanelId(key: HarnessTabKey) {
    return `${harnessTabsId}-panel-${key}`;
  }

  function viewerTabId(key: ViewerTabKey) {
    return `${viewerTabsId}-tab-${key}`;
  }

  function viewerPanelId(key: ViewerTabKey) {
    return `${viewerTabsId}-panel-${key}`;
  }

  function handleRetryOutput() {
    if (!activeCaseId) return;
    const agentRunId = activeOutputState?.agentRunId ?? activeAgentRunId;
    if (!agentRunId) return;
    void fetchCaseOutput(activeCaseId, agentRunId);
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-hidden">
      <SegmentedTabs
        idBase={harnessTabsId}
        tabs={harnessTabs}
        value={activeHarnessTab}
        onChange={setActiveHarnessTab}
        ariaLabel="Test harness tabs"
        className="max-w-sm"
      />
      <span className="sr-only">{agentName}</span>

      <div
        id={harnessPanelId('cases')}
        role="tabpanel"
        aria-labelledby={harnessTabId('cases')}
        hidden={activeHarnessTab !== 'cases'}
        className="h-full min-h-0"
      >
        <div className="grid h-full grid-cols-5 grid-rows-10 overflow-y-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="col-span-3 row-span-10 min-h-0 overflow-auto border-r border-slate-200 pb-6">
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

          <div className="col-span-2 row-span-3 border-b border-slate-200 px-6 py-4 text-slate-900">
            <div className="flex flex-wrap items-center justify-between gap-6">
              <div>
                <p className="text-[11px] uppercase tracking-[0.3em] text-slate-900/70">Harness panel</p>
                <h3 className="text-2xl font-semibold">Start Test Run</h3>
                <p className="text-sm text-slate-900/70">
                  {selectedCases.length} case{selectedCases.length === 1 ? '' : 's'} selected
                </p>

                <div className="mt-3 flex items-center gap-2">
                  <label htmlFor={modelSelectId} className="text-xs font-semibold text-slate-700">
                    Model
                  </label>
                  <select
                    id={modelSelectId}
                    value={selectedModelId}
                    onChange={(e) => setSelectedModelId(e.target.value)}
                    disabled={modelsStatus !== 'success' || runPhase === 'running' || models.length === 0}
                    className="min-w-52 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                  >
                    {modelsStatus === 'loading' ? <option value="">Loading…</option> : null}
                    {modelsStatus === 'error' ? <option value="">Unavailable</option> : null}
                    {modelsStatus === 'success'
                      ? models.map((model) => (
                          <option key={model.id} value={model.id}>
                            {model.id} ({model.provider})
                          </option>
                        ))
                      : null}
                  </select>
                </div>
              </div>

              <button
                type="button"
                onClick={() => onStart(selectedModelId || undefined)}
                disabled={runPhase === 'running' || !selectedCases.length}
                className={`inline-flex items-center gap-2 rounded-2xl px-5 py-2 text-xs font-semibold shadow-slate-900/40 backdrop-blur transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-white ${
                  runPhase === 'running'
                    ? 'cursor-not-allowed bg-slate-200 text-slate-600'
                    : 'bg-PrimaryBlue text-white hover:scale-[1.02] hover:bg-PrimaryBlue/90 disabled:cursor-not-allowed disabled:opacity-60'
                }`}
              >
                <span>{runPhase === 'running' ? 'Running' : runPhase === 'done' ? 'Re Run' : 'Start'}</span>
                <span
                  className={`inline-flex h-2.5 w-2.5 rounded-full ${
                    runPhase === 'running' ? 'bg-orange-400' : 'bg-emerald-400'
                  }`}
                />
              </button>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-4">
              {[
                { label: 'Total cases', value: totals.total },
                { label: 'Running', value: totals.running },
                { label: 'Completed', value: totals.completed },
                { label: 'Queued', value: totals.queued },
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

          <div className="col-span-2 row-span-7 min-h-0 overflow-hidden p-4">
            <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-white p-3">
              <SegmentedTabs
                idBase={viewerTabsId}
                tabs={viewerTabs}
                value={activeViewerTab}
                onChange={setActiveViewerTab}
                ariaLabel="Case inspection views"
                className="max-w-md"
              />

              <div className="mt-3 min-h-0 flex-1">
                <div
                  id={viewerPanelId('case_details')}
                  role="tabpanel"
                  aria-labelledby={viewerTabId('case_details')}
                  hidden={activeViewerTab !== 'case_details'}
                  className="h-full min-h-0 overflow-auto"
                >
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
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
                </div>

                <div
                  id={viewerPanelId('test_traces')}
                  role="tabpanel"
                  aria-labelledby={viewerTabId('test_traces')}
                  hidden={activeViewerTab !== 'test_traces'}
                  className="h-full min-h-0 overflow-hidden"
                >
                  <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="shrink-0 text-xs font-semibold text-slate-900">Test traces</p>
                    <div className="mt-2 min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-100 bg-white p-3">
                      {activeAgentRunId ? (
                        <AgentTracesComponent runId={activeAgentRunId} />
                      ) : activeCaseId ? (
                        <p className="text-xs text-slate-600">
                          {runPhase === 'running'
                            ? 'Waiting for this case to start streaming traces.'
                            : 'No agent run yet for this case. Start the run to stream traces.'}
                        </p>
                      ) : (
                        <p className="text-xs text-slate-600">Select a test case to view its traces.</p>
                      )}
                    </div>
                  </div>
                </div>

                <div
                  id={viewerPanelId('outputs')}
                  role="tabpanel"
                  aria-labelledby={viewerTabId('outputs')}
                  hidden={activeViewerTab !== 'outputs'}
                  className="h-full min-h-0 overflow-hidden"
                >
                  <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="shrink-0 text-xs font-semibold text-slate-900">Outputs</p>
                    <div className="mt-2 min-h-0 flex-1 overflow-auto rounded-xl border border-slate-100 bg-white p-3">
                      {!activeCaseId ? (
                        <p className="text-xs text-slate-600">Select a test case to view its output.</p>
                      ) : activeOutputState?.status === 'loading' ? (
                        <p className="text-xs text-slate-600">Loading output…</p>
                      ) : activeOutputState?.status === 'error' ? (
                        <div className="space-y-3">
                          <p className="text-xs text-rose-700">
                            {activeOutputState.error ?? 'Failed to load output.'}
                          </p>
                          <button
                            type="button"
                            onClick={handleRetryOutput}
                            disabled={!activeOutputState.agentRunId && !activeAgentRunId}
                            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          >
                            Retry Output Fetch
                          </button>
                        </div>
                      ) : activeOutputState?.status === 'ready' ? (
                        activeOutputState.output ? (
                          <JsonInspector value={activeOutputState.output} />
                        ) : (
                          <p className="text-xs text-slate-600">No output returned for this case.</p>
                        )
                      ) : activeCaseStatus === 'passed' || activeCaseStatus === 'failed' ? (
                        <p className="text-xs text-slate-600">
                          Output not available yet for this case. You can retry fetching it.
                        </p>
                      ) : (
                        <p className="text-xs text-slate-600">
                          Output will appear once this case finishes running.
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        id={harnessPanelId('results')}
        role="tabpanel"
        aria-labelledby={harnessTabId('results')}
        hidden={activeHarnessTab !== 'results'}
        className="h-full min-h-0 overflow-auto"
      >
        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {!runId && runPhase === 'idle' ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Test not run. Please start a test run.
          </div>
        ) : runPhase === 'running' ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Currently running test…
          </div>
        ) : runPhase === 'done' ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Run Summary</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-4">
                {[
                  { label: 'Total', value: runMetrics?.total ?? totals.total },
                  { label: 'Passed', value: runMetrics?.passed ?? totals.completed },
                  { label: 'Failed', value: runMetrics?.failed ?? 0 },
                  {
                    label: 'Pass Rate',
                    value:
                      runMetrics?.pass_rate != null
                        ? `${Math.round(runMetrics.pass_rate * 100)}%`
                        : totals.total
                          ? `${Math.round((totals.completed / totals.total) * 100)}%`
                          : '—',
                  },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-[11px] font-semibold text-slate-500">{stat.label}</p>
                    <p className="text-lg font-semibold text-slate-900">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>

            {runMetrics?.classification ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Classification ({runMetrics.classification.label ?? 'n/a'})
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  {[
                    { label: 'Accuracy', value: runMetrics.classification.accuracy },
                    { label: 'Precision', value: runMetrics.classification.precision },
                    { label: 'Recall', value: runMetrics.classification.recall },
                    { label: 'F1', value: runMetrics.classification.f1 },
                    { label: 'Specificity', value: runMetrics.classification.specificity },
                    { label: 'Evaluated', value: runMetrics.classification.n_eval },
                  ].map((stat) => (
                    <div key={stat.label} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-[11px] font-semibold text-slate-500">{stat.label}</p>
                      <p className="text-lg font-semibold text-slate-900">
                        {stat.value == null
                          ? '—'
                          : typeof stat.value === 'number'
                            ? stat.value.toFixed(3)
                            : stat.value}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-[11px] font-semibold text-slate-500">Confusion</p>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-sm font-semibold text-slate-900">
                      <span>TP: {runMetrics.classification.tp ?? 0}</span>
                      <span>TN: {runMetrics.classification.tn ?? 0}</span>
                      <span>FP: {runMetrics.classification.fp ?? 0}</span>
                      <span>FN: {runMetrics.classification.fn ?? 0}</span>
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-[11px] font-semibold text-slate-500">Excluded</p>
                    <div className="mt-2 space-y-1 text-sm font-semibold text-slate-900">
                      <p>Exec failed: {runMetrics.classification.excluded?.exec_failed ?? 0}</p>
                      <p>Invalid pred: {runMetrics.classification.excluded?.invalid_pred ?? 0}</p>
                      <p>Other: {runMetrics.classification.excluded?.other ?? 0}</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Results not available yet.
          </div>
        )}
      </div>
    </div>
  );
}
