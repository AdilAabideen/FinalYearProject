import { useCallback, useEffect, useRef, useState } from 'react';
import type { MasTestCaseRead, MasTestRunMetrics, MasTestRunResults } from '../../../types/masTests';
import { masTestService } from '../../../services/masTestService';
import type { MasCatalogDetail } from '../../../types/mas';
import { MasDiagram } from './MasDiagram';
import type {
  ActiveHandoffEdges,
  AgentRunningStatus,
  BoundaryEdgeHighlights,
} from './MasDetailSplitView';
import { API_BASE_URL } from '../../../config/env';
import { extractCaseId, extractDiff, extractPassed } from '../../agents/utils/testRunStream';
import { asString, isRecord } from '../../agents/utils/runResult';
import { masRunService } from '../../../services/masRunService';
import type { SwarmRunMetricsRead } from '../../../types/masRuns';
import { MasTestCaseSelectionPanel } from './MasTestCaseSelectionPanel';
import { MasTabs } from './MasTabs';
import { MasSelectedCaseTabs } from './MasSelectedCaseTabs';
import { MasTestRunOverlayCard } from './MasTestRunOverlayCard';
import { MasTestCaseWorkspacePanel } from './MasTestCaseWorkspacePanel';
import { MasTestCaseDetailsPanel } from './MasTestCaseDetailsPanel';
import { MasTestCaseTracesPanel } from './MasTestCaseTracesPanel';
import { MasTestCaseDiffPanel } from './MasTestCaseDiffPanel';
import { MasBatchOutputPanel } from './MasBatchOutputPanel';
import { MasBatchMetricsPanel } from './MasBatchMetricsPanel';
import MasResultsTab from './MasResultsTab';
import MasMetricsTab from './MasMetricsTab';
import { buildInitialAgentStatus } from '../utils/agentState';
import { extractMasTestRunId, extractSwarmRunId } from '../utils/streamParsers';

type MasTestCasesProps = {
  workflow: MasCatalogDetail;
};

type TestCaseTabKey = 'test_case' | 'traces' | 'output' | 'metrics' | 'diff';
type MasTestTabKey = 'test' | 'output' | 'metrics';

type TestCaseTab = {
  key: TestCaseTabKey;
  label: string;
};

type MasTestCaseTab = {
  key: MasTestTabKey;
  label: string;
};

const testCaseTabs: TestCaseTab[] = [
  { key: 'test_case', label: 'Test Case' },
  { key: 'traces', label: 'Traces' },
  { key: 'output', label: 'Output' },
  { key: 'metrics', label: 'Metrics' },
  { key: 'diff', label: 'Difference' },
];

const masTestCaseTabs: MasTestCaseTab[] = [
  { key: 'test', label: 'Tests' },
  { key: 'output', label: 'Mas Output' },
  { key: 'metrics', label: 'Mas Metrics' },
];

type TestCaseTraceRun = {
  swarmRunId: string;
  eventsStreamUrl: string;
};

type TestCaseRunStatus = 'idle' | 'running' | 'passed' | 'failed';

type TestCaseDiffState = {
  status: 'idle' | 'ready' | 'error';
  diff?: Record<string, unknown> | null;
  passed?: boolean | null;
  score?: number | null;
  swarmStatus?: string | null;
  error?: string;
};

type MasRunResultsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: MasTestRunResults };

type MasRunMetricsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: MasTestRunMetrics };

export default function MasTestCases({ workflow }: MasTestCasesProps) {
  const [testCases, setTestCases] = useState<MasTestCaseRead[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const [selectedTestCase, setSelectedTestCase] = useState<MasTestCaseRead | null>(null);
  const [selectedTestCaseIds, setSelectedTestCaseIds] = useState<string[]>([]);
  const [showCaseWorkspace, setShowCaseWorkspace] = useState(false);
  const [activeTab, setActiveTab] = useState<TestCaseTabKey>('test_case');
  const [activeMasTab, setActiveMasTab] = useState<MasTestTabKey>('test');
  const [masTestRunId, setMasTestRunId] = useState<string | null>(null);
  const [startingTests, setStartingTests] = useState(false);
  const [testCaseTraceRuns, setTestCaseTraceRuns] = useState<Record<string, TestCaseTraceRun>>({});
  const [testCaseRunStatuses, setTestCaseRunStatuses] = useState<Record<string, TestCaseRunStatus>>({});
  const [testCaseAgentStatuses, setTestCaseAgentStatuses] = useState<Record<string, AgentRunningStatus>>({});
  const [testCaseHandoffEdges, setTestCaseHandoffEdges] = useState<Record<string, ActiveHandoffEdges>>({});
  const [testCaseBoundaryHighlights, setTestCaseBoundaryHighlights] = useState<
    Record<string, BoundaryEdgeHighlights>
  >({});
  const [testCaseDiffs, setTestCaseDiffs] = useState<Record<string, TestCaseDiffState>>({});
  const [testCaseOutputs, setTestCaseOutputs] = useState<Record<string, Record<string, unknown> | null>>({});
  const [testCaseMetrics, setTestCaseMetrics] = useState<Record<string, SwarmRunMetricsRead | null>>({});
  const [masRunResultsState, setMasRunResultsState] = useState<MasRunResultsState>({ status: 'idle' });
  const [masRunMetricsState, setMasRunMetricsState] = useState<MasRunMetricsState>({ status: 'idle' });
  const runStreamRef = useRef<EventSource | null>(null);
  const doneAbortRefs = useRef<Record<string, AbortController>>({});
  const resultsAbortRef = useRef<AbortController | null>(null);
  const batchMetricsAbortRef = useRef<AbortController | null>(null);

  const visibleTestCases =
    selectedTestCaseIds.length > 0
      ? testCases.filter((testCase) => selectedTestCaseIds.includes(testCase.id))
      : [];

  const selectedTraceRun = selectedTestCase ? testCaseTraceRuns[selectedTestCase.id] ?? null : null;
  const selectedAgentStatus = selectedTestCase
    ? testCaseAgentStatuses[selectedTestCase.id] ?? buildInitialAgentStatus(workflow.participating_agents)
    : buildInitialAgentStatus(workflow.participating_agents);
  const selectedHandoffEdges = selectedTestCase ? testCaseHandoffEdges[selectedTestCase.id] ?? {} : {};
  const selectedBoundaryHighlights = selectedTestCase
    ? testCaseBoundaryHighlights[selectedTestCase.id] ?? { start: 'idle', end: 'idle' }
    : ({ start: 'idle', end: 'idle' } as const);
  const selectedTestCaseStatus = selectedTestCase ? testCaseRunStatuses[selectedTestCase.id] ?? 'idle' : 'idle';
  const selectedTestCaseDiffState = selectedTestCase ? testCaseDiffs[selectedTestCase.id] : undefined;
  const selectedTestCaseOutput = selectedTestCase ? testCaseOutputs[selectedTestCase.id] ?? null : null;
  const selectedTestCaseMetrics = selectedTestCase ? testCaseMetrics[selectedTestCase.id] ?? null : null;
  const selectedTestCaseId = selectedTestCase?.id ?? null;

  const selectedDiffRecord =
    selectedTestCaseDiffState?.status === 'ready' && isRecord(selectedTestCaseDiffState.diff)
      ? selectedTestCaseDiffState.diff
      : null;
  const expectedAnswerRecord =
    selectedDiffRecord && isRecord(selectedDiffRecord.expected_answer)
      ? selectedDiffRecord.expected_answer
      : null;
  const actualAnswerRecord =
    selectedDiffRecord && isRecord(selectedDiffRecord.actual_answer)
      ? selectedDiffRecord.actual_answer
      : null;
  const expectedAcuity =
    expectedAnswerRecord &&
    (typeof expectedAnswerRecord.acuity === 'string' || typeof expectedAnswerRecord.acuity === 'number')
      ? String(expectedAnswerRecord.acuity)
      : '—';
  const actualFinalEsiLevel =
    actualAnswerRecord &&
    (typeof actualAnswerRecord.final_esi_level === 'string' ||
      typeof actualAnswerRecord.final_esi_level === 'number')
      ? String(actualAnswerRecord.final_esi_level)
      : '—';
  const masRunResults = masRunResultsState.status === 'ready' ? masRunResultsState.data : null;
  const masRunMetrics = masRunMetricsState.status === 'ready' ? masRunMetricsState.data : null;
  const ranCount = Object.values(testCaseRunStatuses).filter(
    (status) => status === 'passed' || status === 'failed',
  ).length;
  const passedCount = Object.values(testCaseRunStatuses).filter((status) => status === 'passed').length;
  const failedCount = Object.values(testCaseRunStatuses).filter((status) => status === 'failed').length;
  const toRunCount = selectedTestCaseIds.length - ranCount;

  const fetchMasRunResults = useCallback(async (runId: string) => {
    resultsAbortRef.current?.abort();
    const ac = new AbortController();
    resultsAbortRef.current = ac;
    setMasRunResultsState({ status: 'loading' });

    try {
      const data = await masTestService.getRunResults(runId, ac.signal);
      if (ac.signal.aborted) return;
      setMasRunResultsState({ status: 'ready', data });
    } catch (error) {
      if (ac.signal.aborted) return;
      setMasRunResultsState({
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to load MAS test run results',
      });
    } finally {
      if (resultsAbortRef.current === ac) {
        resultsAbortRef.current = null;
      }
    }
  }, []);

  const fetchMasRunMetrics = useCallback(async (runId: string) => {
    batchMetricsAbortRef.current?.abort();
    const ac = new AbortController();
    batchMetricsAbortRef.current = ac;
    setMasRunMetricsState({ status: 'loading' });

    try {
      const data = await masTestService.getRunMetrics(runId, ac.signal);
      if (ac.signal.aborted) return;
      setMasRunMetricsState({ status: 'ready', data });
    } catch (error) {
      if (ac.signal.aborted) return;
      setMasRunMetricsState({
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to load MAS test run metrics',
      });
    } finally {
      if (batchMetricsAbortRef.current === ac) {
        batchMetricsAbortRef.current = null;
      }
    }
  }, []);

  const handleMasDone = useCallback(async (testCaseId: string, swarmRunId: string) => {
    const outputResponse = await fetch(
      `${API_BASE_URL}/api/swarm-runs/${encodeURIComponent(swarmRunId)}/final-output`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      },
    );

    if (!outputResponse.ok) {
      const message = await outputResponse.text();
      throw new Error(message || 'Failed to fetch MAS final output');
    }

    const output = (await outputResponse.json()) as Record<string, unknown>;
    setTestCaseOutputs((prev) => ({
      ...prev,
      [testCaseId]: output,
    }));

    doneAbortRefs.current[testCaseId]?.abort();
    const ac = new AbortController();
    doneAbortRefs.current[testCaseId] = ac;

    try {
      const metrics = await masRunService.getMasRunMetrics(swarmRunId, ac.signal);
      if (ac.signal.aborted) return;
      setTestCaseMetrics((prev) => ({
        ...prev,
        [testCaseId]: metrics,
      }));
    } finally {
      if (doneAbortRefs.current[testCaseId] === ac) {
        delete doneAbortRefs.current[testCaseId];
      }
    }
  }, []);

  function buildSwarmEventsStreamUrl(swarmRunId: string) {
    return `${API_BASE_URL}/api/swarm-runs/${encodeURIComponent(swarmRunId)}/events/stream`;
  }

  function bindCaseToSwarmRun(testCaseId: string, swarmRunId: string) {
    setTestCaseTraceRuns((prev) => ({
      ...prev,
      [testCaseId]: {
        swarmRunId,
        eventsStreamUrl: buildSwarmEventsStreamUrl(swarmRunId),
      },
    }));
    setTestCaseAgentStatuses((prev) => ({
      ...prev,
      [testCaseId]: buildInitialAgentStatus(workflow.participating_agents),
    }));
    setTestCaseHandoffEdges((prev) => ({
      ...prev,
      [testCaseId]: {},
    }));
    setTestCaseBoundaryHighlights((prev) => ({
      ...prev,
      [testCaseId]: { start: 'idle', end: 'idle' },
    }));
  }

  async function startSelectedTests() {
    setActiveTab('traces');
    if (selectedTestCaseIds.length === 0) return;

    runStreamRef.current?.close();
    setStartingTests(true);
    setMasTestRunId(null);
    setTestCaseTraceRuns({});
    setTestCaseRunStatuses({});
    setTestCaseAgentStatuses({});
    setTestCaseHandoffEdges({});
    setTestCaseBoundaryHighlights({});
    setTestCaseDiffs({});
    setTestCaseOutputs({});
    setTestCaseMetrics({});
    setMasRunResultsState({ status: 'idle' });
    setMasRunMetricsState({ status: 'idle' });
    for (const controller of Object.values(doneAbortRefs.current)) {
      controller.abort();
    }
    doneAbortRefs.current = {};
    resultsAbortRef.current?.abort();
    resultsAbortRef.current = null;
    batchMetricsAbortRef.current?.abort();
    batchMetricsAbortRef.current = null;

    try {
      const response = await fetch(`${API_BASE_URL}/api/mas-tests/runs/start`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow_id: workflow.metadata.workflow_id,
          case_ids: selectedTestCaseIds,
        }),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || 'Failed to start MAS test run');
      }

      const payload = (await response.json()) as unknown;
      const runId = extractMasTestRunId(payload);
      if (!runId) {
        throw new Error('MAS test run id was not returned');
      }

      setMasTestRunId(runId);

      const source = new EventSource(
        `${API_BASE_URL}/api/mas-tests/runs/${encodeURIComponent(runId)}/stream`,
      );
      runStreamRef.current = source;

      const parseEventPayload = (event: MessageEvent<string>) => {
        try {
          const parsed = JSON.parse(event.data) as unknown;
          return isRecord(parsed) ? parsed : null;
        } catch {
          return null;
        }
      };

      const handleCaseStartPayload = (payloadRecord: Record<string, unknown>) => {
        const testCaseId = extractCaseId(payloadRecord);
        const swarmRunId = extractSwarmRunId(payloadRecord);
        if (!testCaseId || !swarmRunId) return;
        setTestCaseRunStatuses((prev) => ({
          ...prev,
          [testCaseId]: 'running',
        }));
        bindCaseToSwarmRun(testCaseId, swarmRunId);
      };

      const handleCaseDonePayload = (payloadRecord: Record<string, unknown>) => {
        const testCaseId = extractCaseId(payloadRecord);
        if (!testCaseId) return;
        const passed = extractPassed(payloadRecord);
        const diff = extractDiff(payloadRecord);
        const score =
          typeof payloadRecord.score === 'number'
            ? payloadRecord.score
            : isRecord(payloadRecord.result) && typeof payloadRecord.result.score === 'number'
              ? payloadRecord.result.score
              : isRecord(payloadRecord.payload_json) && typeof payloadRecord.payload_json.score === 'number'
                ? payloadRecord.payload_json.score
                : null;
        const swarmStatus =
          asString(payloadRecord.swarm_status) ??
          (isRecord(payloadRecord.result) ? asString(payloadRecord.result.swarm_status) : undefined) ??
          (isRecord(payloadRecord.payload_json) ? asString(payloadRecord.payload_json.swarm_status) : undefined) ??
          null;

        setTestCaseRunStatuses((prev) => ({
          ...prev,
          [testCaseId]: passed ? 'passed' : 'failed',
        }));
        setTestCaseDiffs((prev) => ({
          ...prev,
          [testCaseId]:
            diff && isRecord(diff)
              ? {
                status: 'ready',
                diff,
                passed,
                score,
                swarmStatus,
              }
              : {
                status: 'idle',
                passed,
                score,
                swarmStatus,
              },
        }));
      };

      source.addEventListener('case_start', (event) => {
        const payloadRecord = parseEventPayload(event as MessageEvent<string>);
        if (!payloadRecord) return;
        handleCaseStartPayload(payloadRecord);
      });

      source.addEventListener('case_done', (event) => {
        const payloadRecord = parseEventPayload(event as MessageEvent<string>);
        if (!payloadRecord) return;
        handleCaseDonePayload(payloadRecord);
      });

      source.addEventListener('message', (event) => {
        const payloadRecord = parseEventPayload(event as MessageEvent<string>);
        if (!payloadRecord) return;

        const eventType =
          asString(payloadRecord.event_type) ??
          (isRecord(payloadRecord.result) ? asString(payloadRecord.result.event_type) : undefined) ??
          (isRecord(payloadRecord.payload_json) ? asString(payloadRecord.payload_json.event_type) : undefined);

        if (eventType === 'case_start') {
          handleCaseStartPayload(payloadRecord);
        }
        if (eventType === 'case_done') {
          handleCaseDonePayload(payloadRecord);
        }
      });

      source.addEventListener('done', () => {
        source.close();
        if (runStreamRef.current === source) runStreamRef.current = null;
        void fetchMasRunResults(runId);
        void fetchMasRunMetrics(runId);
      });

      source.onerror = () => {
        console.warn('MAS test run stream disconnected; waiting for SSE reconnect');
      };
    } catch (error) {
      console.error('Failed to start MAS test run', error);
    } finally {
      setStartingTests(false);
    }
  }

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    async function loadTestCases(workflowId: string) {
      setLoading(true);

      try {
        if (workflowId) {
          const loadedTestCases = await masTestService.listTestCases({ workflow_id: workflowId }, ac.signal);
          if (ac.signal.aborted) return;
          setTestCases(loadedTestCases);
          setSelectedTestCase((prev) => prev ?? loadedTestCases[0] ?? null);
          setSelectedTestCaseIds((prev) =>
            prev.length ? prev.filter((id) => loadedTestCases.some((testCase) => testCase.id === id)) : [],
          );
        }
      } catch (error) {
        if (ac.signal.aborted) return;
        console.error('Error occurred', error);
        setTestCases([]);
      } finally {
        if (!ac.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadTestCases(workflow?.metadata.workflow_id);

    return () => {
      ac.abort();
    };
  }, [workflow?.metadata.workflow_id]);

  useEffect(() => {
    if (!showCaseWorkspace) return;

    setSelectedTestCase((prev) => {
      if (prev && visibleTestCases.some((testCase) => testCase.id === prev.id)) {
        return prev;
      }
      return visibleTestCases[0] ?? null;
    });
  }, [showCaseWorkspace, visibleTestCases]);

  useEffect(() => {
    return () => {
      runStreamRef.current?.close();
      for (const controller of Object.values(doneAbortRefs.current)) {
        controller.abort();
      }
      doneAbortRefs.current = {};
      resultsAbortRef.current?.abort();
      resultsAbortRef.current = null;
      batchMetricsAbortRef.current?.abort();
      batchMetricsAbortRef.current = null;
    };
  }, []);

  function toggleTestCaseSelection(testCaseId: string) {
    setSelectedTestCaseIds((prev) =>
      prev.includes(testCaseId)
        ? prev.filter((id) => id !== testCaseId)
        : [...prev, testCaseId],
    );
  }

  function toggleSelectAllTestCases() {
    setSelectedTestCaseIds((prev) =>
      prev.length === testCases.length ? [] : testCases.map((testCase) => testCase.id),
    );
  }

  const updateSelectedAgentStatus = useCallback(
    (value: AgentRunningStatus | ((prev: AgentRunningStatus) => AgentRunningStatus)) => {
      if (!selectedTestCaseId) return;

      setTestCaseAgentStatuses((prev) => {
        const current = prev[selectedTestCaseId] ?? buildInitialAgentStatus(workflow.participating_agents);
        const nextValue = typeof value === 'function' ? value(current) : value;
        return {
          ...prev,
          [selectedTestCaseId]: nextValue,
        };
      });
    },
    [selectedTestCaseId, workflow.participating_agents],
  );

  const updateSelectedHandoffEdges = useCallback(
    (value: ActiveHandoffEdges | ((prev: ActiveHandoffEdges) => ActiveHandoffEdges)) => {
      if (!selectedTestCaseId) return;

      setTestCaseHandoffEdges((prev) => {
        const current = prev[selectedTestCaseId] ?? {};
        const nextValue = typeof value === 'function' ? value(current) : value;
        return {
          ...prev,
          [selectedTestCaseId]: nextValue,
        };
      });
    },
    [selectedTestCaseId],
  );

  const updateSelectedBoundaryHighlights = useCallback(
    (
      value:
        | BoundaryEdgeHighlights
        | ((prev: BoundaryEdgeHighlights) => BoundaryEdgeHighlights),
    ) => {
      if (!selectedTestCaseId) return;

      setTestCaseBoundaryHighlights((prev) => {
        const current = prev[selectedTestCaseId] ?? { start: 'idle', end: 'idle' };
        const nextValue = typeof value === 'function' ? value(current) : value;
        return {
          ...prev,
          [selectedTestCaseId]: nextValue,
        };
      });
    },
    [selectedTestCaseId],
  );

  const handleSelectedMasDone = useCallback(async () => {
    if (!selectedTestCaseId || !selectedTraceRun) return;
    await handleMasDone(selectedTestCaseId, selectedTraceRun.swarmRunId);
  }, [handleMasDone, selectedTestCaseId, selectedTraceRun]);

  if (loading) {
    return (
      <div className="flex min-h-[560px] h-full flex-1 items-center justify-center bg-white p-6">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-6 py-8 text-center shadow-sm">
          <p className="text-sm font-semibold text-slate-900">Loading test cases…</p>
        </div>
      </div>
    );
  }

  if (testCases.length === 0) {
    return (
      <div className="flex min-h-[560px] h-full flex-1 items-center justify-center bg-white p-6">
        <div className="flex items-stretch border-b border-slate-200 bg-white">No tests</div>
      </div>
    );
  }

  if (!showCaseWorkspace) {
    const allSelected = testCases.length > 0 && selectedTestCaseIds.length === testCases.length;

    return (
      <MasTestCaseSelectionPanel
        testCases={testCases}
        selectedTestCaseIds={selectedTestCaseIds}
        allSelected={allSelected}
        onToggleAll={toggleSelectAllTestCases}
        onToggleOne={toggleTestCaseSelection}
        onOpenSelectedCases={() => setShowCaseWorkspace(true)}
      />
    );
  }

  return visibleTestCases.length > 0 ? (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-white">
      <MasTabs
        tabs={masTestCaseTabs}
        activeKey={activeMasTab}
        onChange={setActiveMasTab}
        minTabWidthClassName="min-w-28"
        wrapperClassName="border-b border-slate-200"
        buttonClassName="flex h-full cursor-pointer items-center border-r border-t border-slate-200 px-4 py-2 text-left transition-colors"
      />

      {activeMasTab === 'output' ? (
        <div className="min-h-0 flex-1 overflow-auto bg-white">
          <MasBatchOutputPanel
            status={masRunResultsState.status}
            error={masRunResultsState.status === 'error' ? masRunResultsState.error : undefined}
            results={masRunResults}
          />
        </div>
      ) : activeMasTab === 'metrics' ? (
        <div className="min-h-0 flex-1 overflow-auto bg-white">
          <MasBatchMetricsPanel
            status={masRunMetricsState.status}
            error={masRunMetricsState.status === 'error' ? masRunMetricsState.error : undefined}
            metrics={masRunMetrics}
          />
        </div>
      ) : (
        <>
          <MasSelectedCaseTabs
            visibleTestCases={visibleTestCases}
            selectedTestCaseId={selectedTestCaseId}
            runStatuses={testCaseRunStatuses}
            onSelectCase={setSelectedTestCase}
          />

          <div className="grid min-h-0 flex-1 grid-cols-6 grid-rows-1 overflow-hidden">
            <div className="relative col-span-4 h-full min-h-0 flex-1 overflow-hidden rounded-none bg-white">
              <MasDiagram
                workflow={workflow}
                agentStatus={selectedAgentStatus}
                activeHandoffEdges={selectedHandoffEdges}
                boundaryEdgeHighlights={selectedBoundaryHighlights}
              />
              <MasTestRunOverlayCard
                selectedCount={selectedTestCaseIds.length}
                ranCount={ranCount}
                toRunCount={toRunCount}
                passedCount={passedCount}
                failedCount={failedCount}
                masTestRunId={masTestRunId}
                startingTests={startingTests}
                onStartTests={() => {
                  void startSelectedTests();
                }}
              />
            </div>

            <MasTestCaseWorkspacePanel
              tabs={testCaseTabs}
              activeTab={activeTab}
              onChangeTab={setActiveTab}
            >
              {activeTab === 'test_case' ? (
                <MasTestCaseDetailsPanel testCase={selectedTestCase} />
              ) : activeTab === 'traces' ? (
                <MasTestCaseTracesPanel
                  testCase={selectedTestCase}
                  traceRun={selectedTraceRun}
                  agentNames={workflow.participating_agents}
                  setAgentStatus={updateSelectedAgentStatus}
                  setActiveHandoffEdges={updateSelectedHandoffEdges}
                  setBoundaryEdgeHighlights={updateSelectedBoundaryHighlights}
                  onMasDone={handleSelectedMasDone}
                />
              ) : activeTab === 'output' ? (
                <div className="h-full min-h-0 overflow-auto">
                  <MasResultsTab input={selectedTestCase?.inputJson ?? {}} output={selectedTestCaseOutput} />
                </div>
              ) : activeTab === 'diff' ? (
                <div className="h-full min-h-0 overflow-auto p-0">
                  <MasTestCaseDiffPanel
                    hasSelectedCase={selectedTestCase != null}
                    diffState={selectedTestCaseDiffState}
                    runStatus={selectedTestCaseStatus}
                    expectedAcuity={expectedAcuity}
                    actualFinalEsiLevel={actualFinalEsiLevel}
                  />
                </div>
              ) : (
                <div className="h-full min-h-0 overflow-auto">
                  <MasMetricsTab metrics={selectedTestCaseMetrics} />
                </div>
              )}
            </MasTestCaseWorkspacePanel>
          </div>
        </>
      )}
    </div>
  ) : (
    <div className="flex min-h-[560px] h-full flex-1 items-center justify-center bg-white p-6">
      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-6 py-8 text-center shadow-sm">
        <p className="text-sm font-semibold text-slate-900">No selected test cases</p>
        <p className="mt-2 text-sm text-slate-500">
          Go back and choose at least one test case to open the workspace.
        </p>
      </div>
    </div>
  );
}
