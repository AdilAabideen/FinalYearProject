import { useCallback, useEffect, useId, useMemo, useState } from 'react';
import type { AgentTestCaseRead, AgentTestRunBatchMetricsRead } from '../../../types/agentTests';
import { API_BASE_URL } from '../../../config/env';
import { agentTestService } from '../../../services/agentTestService';
import { agentRunService } from '../../../services/agentRunService';
import { SegmentedTabs } from '../../../shared/ui/SegmentedTabs';
import { useModels } from '../hooks/useModels';
import {
  asString,
  buildResultViewModel,
  getAdditionalOutputEntries,
  getAgentDecisionConfig,
  isRecord,
} from '../utils/runResult';
import { formatPercent } from '../utils/format';
import { getReliabilitySummaryView } from '../utils/reliability';
import {
  extractAgentRunId,
  extractCaseId,
  extractDiff,
  extractMetrics,
  extractPassed,
} from '../utils/testRunStream';
import { resolveDiffRenderer } from '../utils/testRunDiff';
import type { AgentStatCardTone } from './shared/AgentStatCard';
import { AgentTestHarnessPanel } from './agent-test-run-drawer/AgentTestHarnessPanel';
import { AgentTestRunResultsPanel } from './agent-test-run-drawer/AgentTestRunResultsPanel';
import { AgentTestRunMetricsPanel } from './agent-test-run-drawer/AgentTestRunMetricsPanel';

type HarnessTabKey = 'cases' | 'results' | 'run_metrics';
type ViewerTabKey = 'case_details' | 'test_traces' | 'outputs' | 'diff' | 'metrics';
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

type CaseMetricsState = {
  status: 'idle' | 'loading' | 'ready' | 'error';
  agentRunId?: string;
  metrics?: Record<string, unknown> | null;
  error?: string;
}

type CaseDiffState = {
  status: 'idle' | 'loading' | 'ready' | 'error';
  agentRunId?: string;
  diff?: Record<string, unknown> | null;
  error?: string;
}

type AggregatedRunMetricsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: AgentTestRunBatchMetricsRead };

const harnessTabs: Array<{ key: HarnessTabKey; label: string }> = [
  { key: 'cases', label: 'Test Cases' },
  { key: 'results', label: 'Test Results' },
  { key: 'run_metrics', label: 'Run Metrics' },
];

const viewerTabs: Array<{ key: ViewerTabKey; label: string }> = [
  { key: 'case_details', label: 'Details' },
  { key: 'test_traces', label: 'Test Traces' },
  { key: 'outputs', label: 'Outputs' },
  { key: 'diff', label: 'Diff' },
  { key: 'metrics', label: 'Metrics' },
];


type AgentTestRunDrawerProps = {
  agentName: string;
  runId: string | null;
  selectedCases: AgentTestCaseRead[];
  busy: boolean;
  error: string | null;
  onStart: (modelId?: string) => void | Promise<void>;
};

// Renders the agent test run drawer.
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
  const [metricsByCaseId, setMetricsByCaseId] = useState<Record<string, CaseMetricsState>>({});
  const [diffByCaseId, setDiffByCaseId] = useState<Record<string, CaseDiffState>>({});
  const [aggregatedRunMetricsState, setAggregatedRunMetricsState] =
    useState<AggregatedRunMetricsState>({ status: 'idle' });

  const { models, status: modelsStatus, selectedModelId, setSelectedModelId } = useModels();
  const selectedCaseIdsKey = useMemo(
    () => selectedCases.map((testCase) => testCase.id).join('|'),
    [selectedCases],
  );

  const totals = useMemo(() => {
    const total = selectedCases.length;
    const completed = Object.values(caseStates).filter(
      (c) => c.status === 'passed' || c.status === 'failed',
    ).length;
    const running = Object.values(caseStates).filter((c) => c.status === 'running').length;
    return { total, completed, running, queued: Math.max(total - completed - running, 0) };
  }, [caseStates, selectedCases.length]);


// Manages callback.
  const insertDiff = useCallback((caseId: string, agentRunId: string | undefined, diff: Record<string, unknown>) => {

    try {
      setDiffByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: 'ready',
          agentRunId,
          diff,
        },
      }));
    } catch (e: unknown) {
      setDiffByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: 'error',
          agentRunId,
          error: e instanceof Error ? e.message : 'Failed to load diff',
        },
      }));
    }
    
  }, []);

// Manages callback.
  const fetchAggregatedRunMetrics = useCallback(async (targetRunId: string) => {
    if (!targetRunId) return;
    setAggregatedRunMetricsState({ status: 'loading' });
    try {
      const data = await agentTestService.getRunBatchMetrics(targetRunId);
      setAggregatedRunMetricsState({ status: 'ready', data });
    } catch (e: unknown) {
      setAggregatedRunMetricsState({
        status: 'error',
        error: e instanceof Error ? e.message : 'Failed to load run metrics',
      });
    }
  }, []);

  const fetchCaseOutputAndMetrics = useCallback(
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
      catch (e: unknown) {
        setOutputsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'error',
            agentRunId,
            error: e instanceof Error ? e.message : 'Failed to load output',
          },
        }));
      }

      try {
        const metrics = await agentRunService.getAgentRunMetrics(agentRunId);
        setMetricsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'ready',
            agentRunId,
            metrics: metrics,
          },
        }));
      }
      catch (e: unknown) {
        setMetricsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'error',
            agentRunId,
            error: e instanceof Error ? e.message : 'Failed to load metrics',
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
    setMetricsByCaseId({});
    setDiffByCaseId({});
    setAggregatedRunMetricsState({ status: runId ? 'loading' : 'idle' });
    setActiveViewerTab('case_details');
    setActiveHarnessTab('cases');
  }, [selectedCaseIdsKey, runId]);

  useEffect(() => {
    if (!runId) {
      setAggregatedRunMetricsState({ status: 'idle' });
      return;
    }
    void fetchAggregatedRunMetrics(runId);
  }, [runId, fetchAggregatedRunMetrics]);

  useEffect(() => {
    if (!runId) return undefined;

    const caseRunMap: Record<string, string> = {};
    const url = `${API_BASE_URL}/api/tests/runs/${encodeURIComponent(runId)}/stream`;
    const source = new EventSource(url);
    setRunPhase('running');

// Handles case start payload.
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
      setMetricsByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: prev[caseId]?.status === 'ready' ? 'ready' : 'idle',
          agentRunId,
          metrics: prev[caseId]?.metrics,
          error: prev[caseId]?.error,
        },
      }));
      setDiffByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: prev[caseId]?.status === 'ready' ? 'ready' : 'idle',
          agentRunId,
          diff: prev[caseId]?.diff,
          error: prev[caseId]?.error,
        },
      }));
      setActiveCaseId((current) => current ?? caseId);
    };

// Handles case done payload.
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
        setMetricsByCaseId((prev) => ({
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
      void fetchCaseOutputAndMetrics(caseId, agentRunId);
    };

// Handles run done payload.
    const handleRunDonePayload = (payload: Record<string, unknown>) => {
      const metrics = extractMetrics(payload);
      if (metrics) setRunMetrics(metrics);
      setRunPhase('done');
      if (runId) void fetchAggregatedRunMetrics(runId);
    };

// Parses event payload.
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
      if (!payload) return;
      const caseId = extractCaseId(payload);
      if (!caseId) return;
      const agentRunId = extractAgentRunId(payload) ?? caseRunMap[caseId];
      const diff = extractDiff(payload);
      if (diff) insertDiff(caseId, agentRunId, diff);
      handleCaseDonePayload(payload);
    });

    source.addEventListener('run_done', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      if (!payload) return;
      handleRunDonePayload(payload);
    });

    source.addEventListener('message', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      if (!payload) return;


      const eventType =
        asString(payload.event_type) ??
        (isRecord(payload.result) ? asString(payload.result.event_type) : undefined) ??
        (isRecord(payload.payload_json) ? asString(payload.payload_json.event_type) : undefined);

      if (eventType === 'case_start') handleCaseStartPayload(payload);
      if (eventType === 'case_done') {
        const caseId = extractCaseId(payload);
        if (caseId) {
          const agentRunId = extractAgentRunId(payload) ?? caseRunMap[caseId];
          const diff = extractDiff(payload);
          if (diff) insertDiff(caseId, agentRunId, diff);
        }
        handleCaseDonePayload(payload);
      }
      if (eventType === 'run_done') handleRunDonePayload(payload);
    });

    source.addEventListener('done', () => {
      setRunPhase('done');
      source.close();
    });

    source.onerror = () => {
      source.close();
    };

    return () => {
      source.close();
    };
  }, [runId, fetchCaseOutputAndMetrics, insertDiff, fetchAggregatedRunMetrics]);

  const activeCase = useMemo(
    () => selectedCases.find((c) => c.id === activeCaseId),
    [selectedCases, activeCaseId],
  );

  const activeAgentRunId = activeCaseId ? agentRunByCaseId[activeCaseId] ?? null : null;
  const activeOutputState = activeCaseId ? outputsByCaseId[activeCaseId] : undefined;
  const activeMetricsState = activeCaseId ? metricsByCaseId[activeCaseId] : undefined;
  const activeDiffState = activeCaseId ? diffByCaseId[activeCaseId] : undefined;
  const activeCaseStatus = activeCaseId ? caseStates[activeCaseId]?.status : undefined;
  const activeMetricsRecord =
    activeMetricsState?.status === 'ready' && isRecord(activeMetricsState.metrics)
      ? activeMetricsState.metrics
      : null;
  const activeReliabilitySummaryView = useMemo(
    () => getReliabilitySummaryView(activeMetricsRecord, { fallbackCountsToZero: true }),
    [activeMetricsRecord],
  );
  const activeOutputRecord =
    activeOutputState?.status === 'ready' && isRecord(activeOutputState.output)
      ? activeOutputState.output
      : null;
  const decisionConfig = useMemo(() => getAgentDecisionConfig(agentName), [agentName]);
  const diffRenderer = useMemo(() => resolveDiffRenderer(agentName), [agentName]);

  const activeResultView = useMemo(() => {
    if (!activeOutputRecord) return null;
    return buildResultViewModel(activeOutputRecord, decisionConfig, {
      summaryFallback: 'No summary was provided by this case output.',
      justificationFallback: 'No justification was provided by this case output.',
    });
  }, [activeOutputRecord, decisionConfig]);

  const activeAdditionalOutputEntries = useMemo(() => {
    if (!activeOutputRecord) return [];
    return getAdditionalOutputEntries(activeOutputRecord, { decisionConfig });
  }, [activeOutputRecord, decisionConfig]);

// Handles harness tab ID.
  function harnessTabId(key: HarnessTabKey) {
    return `${harnessTabsId}-tab-${key}`;
  }

// Handles harness panel ID.
  function harnessPanelId(key: HarnessTabKey) {
    return `${harnessTabsId}-panel-${key}`;
  }

// Handles viewer tab ID.
  function viewerTabId(key: ViewerTabKey) {
    return `${viewerTabsId}-tab-${key}`;
  }

// Handles viewer panel ID.
  function viewerPanelId(key: ViewerTabKey) {
    return `${viewerTabsId}-panel-${key}`;
  }

// Handles retry output.
  function handleRetryOutput() {
    if (!activeCaseId) return;
    const agentRunId = activeOutputState?.agentRunId ?? activeAgentRunId;
    if (!agentRunId) return;
    void fetchCaseOutputAndMetrics(activeCaseId, agentRunId);
  }

// Handles retry run metrics.
  function handleRetryRunMetrics() {
    if (!runId) return;
    void fetchAggregatedRunMetrics(runId);
  }

  const summaryTotal = runMetrics?.total ?? totals.total;
  const summaryPassed = runMetrics?.passed ?? totals.completed;
  const summaryFailed = runMetrics?.failed ?? Math.max(summaryTotal - summaryPassed, 0);
  const summaryExecFailed = runMetrics?.exec_failed ?? 0;
  const summaryInvalidPred = runMetrics?.invalid_pred ?? 0;
  const summaryPassRate = runMetrics?.pass_rate ?? (summaryTotal > 0 ? summaryPassed / summaryTotal : null);
  const summaryPassRateLabel = formatPercent(summaryPassRate);
  const summaryPassRateTone: AgentStatCardTone =
    summaryPassRate == null ? 'default' : summaryPassRate >= 0.8 ? 'positive' : summaryPassRate >= 0.6 ? 'accent' : 'danger';

  const classification = runMetrics?.classification ?? null;
  const tp = classification?.tp ?? 0;
  const tn = classification?.tn ?? 0;
  const fp = classification?.fp ?? 0;
  const fn = classification?.fn ?? 0;
  const confusionMax = Math.max(tp, tn, fp, fn, 1);

  const aggregatedRunMetrics =
    aggregatedRunMetricsState.status === 'ready' ? aggregatedRunMetricsState.data : null;
  const aggregatedSummary = aggregatedRunMetrics?.summary ?? null;
  const aggregatedFailureReasons = aggregatedSummary?.failureReasonCounts ?? {};
  const aggregatedFailureReasonEntries = Object.entries(aggregatedFailureReasons).sort(([a], [b]) =>
    a.localeCompare(b),
  );

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
        <AgentTestHarnessPanel
          viewerTabsId={viewerTabsId}
          viewerTabs={viewerTabs}
          activeViewerTab={activeViewerTab}
          onChangeViewerTab={setActiveViewerTab}
          viewerTabId={viewerTabId}
          viewerPanelId={viewerPanelId}
          selectedCases={selectedCases}
          activeCaseId={activeCaseId}
          setActiveCaseId={setActiveCaseId}
          caseStates={caseStates}
          selectedCaseCount={selectedCases.length}
          totals={totals}
          modelSelectId={modelSelectId}
          models={models}
          modelsStatus={modelsStatus}
          selectedModelId={selectedModelId}
          setSelectedModelId={setSelectedModelId}
          runPhase={runPhase}
          onStart={onStart}
          activeCase={activeCase ?? null}
          activeAgentRunId={activeAgentRunId}
          activeOutputState={activeOutputState}
          activeMetricsState={activeMetricsState}
          activeDiffState={activeDiffState}
          activeCaseStatus={activeCaseStatus}
          activeResultView={activeResultView}
          activeAdditionalOutputEntries={activeAdditionalOutputEntries}
          activeReliabilitySummaryView={activeReliabilitySummaryView}
          diffRenderer={diffRenderer}
          handleRetryOutput={handleRetryOutput}
        />
      </div>

      <div
        id={harnessPanelId('results')}
        role="tabpanel"
        aria-labelledby={harnessTabId('results')}
        hidden={activeHarnessTab !== 'results'}
        className="h-full min-h-0 overflow-auto"
      >
        <AgentTestRunResultsPanel
          error={error}
          runId={runId}
          runPhase={runPhase}
          runMetrics={runMetrics as Record<string, unknown> | null}
          summaryTotal={summaryTotal}
          summaryPassed={summaryPassed}
          summaryFailed={summaryFailed}
          summaryExecFailed={summaryExecFailed}
          summaryInvalidPred={summaryInvalidPred}
          summaryPassRate={summaryPassRate}
          summaryPassRateLabel={summaryPassRateLabel}
          summaryPassRateTone={summaryPassRateTone}
          agentName={agentName}
          classification={classification}
          tp={tp}
          tn={tn}
          fp={fp}
          fn={fn}
          confusionMax={confusionMax}
        />
      </div>

      <div
        id={harnessPanelId('run_metrics')}
        role="tabpanel"
        aria-labelledby={harnessTabId('run_metrics')}
        hidden={activeHarnessTab !== 'run_metrics'}
        className="h-full min-h-0 overflow-auto"
      >
        <AgentTestRunMetricsPanel
          runId={runId}
          aggregatedRunMetricsState={aggregatedRunMetricsState}
          aggregatedRunMetrics={aggregatedRunMetrics}
          aggregatedSummary={aggregatedSummary}
          aggregatedFailureReasonEntries={aggregatedFailureReasonEntries}
          onRetry={handleRetryRunMetrics}
        />
      </div>
    </div>
  );
}
