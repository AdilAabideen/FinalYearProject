import { useCallback, useEffect, useRef, useState } from 'react';
import type { MasTestCaseRead } from '../../../types/masTests';
import { masTestService } from '../../../services/masTestService';
import type { MasCatalogDetail } from '../../../types/mas';
import { MasDiagram } from './MasDiagram';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import MasTracesTab from './MasTracesTab';
import MasResultsTab from './MasResultsTab';
import MasMetricsTab from './MasMetricsTab';
import type {
  ActiveHandoffEdges,
  AgentRunningStatus,
  BoundaryEdgeHighlights,
} from './MasDetailSplitView';
import { API_BASE_URL } from '../../../config/env';
import { extractCaseId } from '../../agents/utils/testRunStream';
import { asString, isRecord } from '../../agents/utils/runResult';
import { masRunService } from '../../../services/masRunService';
import type { SwarmRunMetricsRead } from '../../../types/masRuns';

type MasTestCasesProps = {
  workflow: MasCatalogDetail;
};

type TestCaseTabKey = 'test_case' | 'traces' | 'output' | 'metrics' | 'diff';

type TestCaseTab = {
  key: TestCaseTabKey;
  label: string;
};

const testCaseTabs: TestCaseTab[] = [
  { key: 'test_case', label: 'Test Case' },
  { key: 'traces', label: 'Traces' },
  { key: 'output', label: 'Output' },
  { key: 'metrics', label: 'Metrics' },
  { key: 'diff', label: 'Difference' },
];

function splitName(name: string) {
  return name.split('-', 1)[0];
}

function buildInitialAgentStatus(agentNames: string[]) {
  const next: AgentRunningStatus = {};
  for (const agentName of agentNames) {
    next[agentName] = 'waiting';
  }
  return next;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

type TestCaseTraceRun = {
  swarmRunId: string;
  eventsStreamUrl: string;
};

type TestCaseRunStatus = 'idle' | 'running' | 'completed';

function extractMasTestRunId(value: unknown) {
  if (!isRecord(value)) return null;

  return (
    asString(value.run_id) ??
    asString(value.id) ??
    (isRecord(value.result) ? asString(value.result.run_id) ?? asString(value.result.id) : undefined) ??
    null
  );
}

function extractSwarmRunId(value: Record<string, unknown>) {
  return (
    asString(value.swarm_run_id) ??
    (isRecord(value.result) ? asString(value.result.swarm_run_id) : undefined) ??
    (isRecord(value.payload_json) ? asString(value.payload_json.swarm_run_id) : undefined) ??
    null
  );
}

export default function MasTestCases({ workflow }: MasTestCasesProps) {
  const [testCases, setTestCases] = useState<MasTestCaseRead[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const [selectedTestCase, setSelectedTestCase] = useState<MasTestCaseRead | null>(null);
  const [selectedTestCaseIds, setSelectedTestCaseIds] = useState<string[]>([]);
  const [showCaseWorkspace, setShowCaseWorkspace] = useState(false);
  const [activeTab, setActiveTab] = useState<TestCaseTabKey>('test_case');
  const [masTestRunId, setMasTestRunId] = useState<string | null>(null);
  const [startingTests, setStartingTests] = useState(false);
  const [testCaseTraceRuns, setTestCaseTraceRuns] = useState<Record<string, TestCaseTraceRun>>({});
  const [testCaseRunStatuses, setTestCaseRunStatuses] = useState<Record<string, TestCaseRunStatus>>({});
  const [testCaseAgentStatuses, setTestCaseAgentStatuses] = useState<Record<string, AgentRunningStatus>>({});
  const [testCaseHandoffEdges, setTestCaseHandoffEdges] = useState<Record<string, ActiveHandoffEdges>>({});
  const [testCaseBoundaryHighlights, setTestCaseBoundaryHighlights] = useState<
    Record<string, BoundaryEdgeHighlights>
  >({});
  const [testCaseOutputs, setTestCaseOutputs] = useState<Record<string, Record<string, unknown> | null>>({});
  const [testCaseMetrics, setTestCaseMetrics] = useState<Record<string, SwarmRunMetricsRead | null>>({});
  const runStreamRef = useRef<EventSource | null>(null);
  const doneAbortRefs = useRef<Record<string, AbortController>>({});

  const selectedTraceRun = selectedTestCase ? testCaseTraceRuns[selectedTestCase.id] ?? null : null;
  const selectedAgentStatus = selectedTestCase
    ? testCaseAgentStatuses[selectedTestCase.id] ?? buildInitialAgentStatus(workflow.participating_agents)
    : buildInitialAgentStatus(workflow.participating_agents);
  const selectedHandoffEdges = selectedTestCase
    ? testCaseHandoffEdges[selectedTestCase.id] ?? {}
    : {};
  const selectedBoundaryHighlights = selectedTestCase
    ? testCaseBoundaryHighlights[selectedTestCase.id] ?? { start: 'idle', end: 'idle' }
    : ({ start: 'idle', end: 'idle' } as const);
  const selectedTestCaseOutput = selectedTestCase ? testCaseOutputs[selectedTestCase.id] ?? null : null;
  const selectedTestCaseMetrics = selectedTestCase ? testCaseMetrics[selectedTestCase.id] ?? null : null;

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
    setActiveTab("traces")
    if (selectedTestCaseIds.length === 0) return;

    runStreamRef.current?.close();
    setStartingTests(true);
    setMasTestRunId(null);
    setTestCaseTraceRuns({});
    setTestCaseRunStatuses({});
    setTestCaseAgentStatuses({});
    setTestCaseHandoffEdges({});
    setTestCaseBoundaryHighlights({});
    setTestCaseOutputs({});
    setTestCaseMetrics({});
    for (const controller of Object.values(doneAbortRefs.current)) {
      controller.abort();
    }
    doneAbortRefs.current = {};

    console.log(
      JSON.stringify({
        workflow_id: workflow.metadata.workflow_id,
        case_ids: selectedTestCaseIds
      })
    )

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
        setTestCaseRunStatuses((prev) => ({
          ...prev,
          [testCaseId]: 'completed',
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

    async function loadTestCases(workflow_id: string) {
      setLoading(true);

      try {
        if (workflow_id) {
          const loadedTestCases = await masTestService.listTestCases(
            { workflow_id },
            ac.signal,
          );
          if (ac.signal.aborted) return;
          setTestCases(loadedTestCases);
          setSelectedTestCase((prev) => prev ?? loadedTestCases[0] ?? null);
          setSelectedTestCaseIds((prev) =>
            prev.length ? prev.filter((id) => loadedTestCases.some((testCase) => testCase.id === id)) : [],
          );
        }
      } catch (e) {
        if (ac.signal.aborted) return;
        console.error('Error occurred', e);
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

  const visibleTestCases =
    selectedTestCaseIds.length > 0
      ? testCases.filter((testCase) => selectedTestCaseIds.includes(testCase.id))
      : [];

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
    };
  }, []);

  function toggleTestCaseSelection(testCaseId: string) {
    setSelectedTestCaseIds((prev) =>
      prev.includes(testCaseId)
        ? prev.filter((id) => id !== testCaseId)
        : [...prev, testCaseId],
    );
  }

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
        <div className="flex items-stretch border-b border-slate-200 bg-white">
          No tests
        </div>
      </div>
    );
  }

  if (!showCaseWorkspace) {
    return (
      <div className="flex h-full min-h-0 flex-col bg-white">
        <div className="border-b border-slate-200 px-6 py-4">
          <p className="text-lg font-semibold text-slate-900">Select Test Cases</p>
          <p className="mt-1 text-sm text-slate-500">
            Choose the cases you want to inspect before opening the workspace.
          </p>
        </div>

        <div className="min-h-0 flex-1">
          <div className="h-full overflow-auto rounded border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Select
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Created
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Updated
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {testCases.map((testCase) => {
                  const checked = selectedTestCaseIds.includes(testCase.id);

                  return (
                    <tr key={testCase.id} className="hover:bg-slate-50/70">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleTestCaseSelection(testCase.id)}
                          className="h-4 w-4 rounded border-slate-300 text-PrimaryBlue focus:ring-PrimaryBlue"
                        />
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-slate-900">
                        {testCase.name}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={[
                            'inline-flex rounded-full border px-3 py-1 text-xs font-semibold',
                            testCase.enabled
                              ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                              : 'border-slate-200 bg-slate-50 text-slate-600',
                          ].join(' ')}
                        >
                          {testCase.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600">
                        {formatDateTime(testCase.createdAt)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600">
                        {formatDateTime(testCase.updatedAt)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4 bg-white">
          <p className="text-sm text-slate-500">
            {selectedTestCaseIds.length} {selectedTestCaseIds.length === 1 ? 'case' : 'cases'} selected
          </p>
          <button
            type="button"
            disabled={selectedTestCaseIds.length === 0}
            onClick={() => setShowCaseWorkspace(true)}
            className={[
              'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold transition',
              selectedTestCaseIds.length === 0
                ? 'cursor-not-allowed bg-slate-100 text-slate-400'
                : 'bg-PrimaryBlue text-white hover:bg-PrimaryBlue/90',
            ].join(' ')}
          >
            Open Selected Cases
          </button>
        </div>
      </div>
    );
  }

  return visibleTestCases.length > 0 ? (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-white">
      <div className="flex shrink-0 flex-row items-start p-0  border-b border-slate-200">
        {visibleTestCases.map((test) => {
          const active = selectedTestCase?.id === test.id;
          const runStatus = testCaseRunStatuses[test.id] ?? 'idle';
          return (
            <button
              key={test.id}
              type="button"
              onClick={() => setSelectedTestCase(test)}
              className={[
                'flex h-full cursor-pointer min-w-36 py-2 items-center border-r  border-t border-slate-200 px-4 text-left transition-colors',
                active ? 'bg-slate-50' : 'bg-white hover:bg-slate-50',
              ].join(' ')}
            >
              <span
                className={[
                  'mr-2 inline-block h-2.5 w-2.5 rounded-full',
                  runStatus === 'completed'
                    ? 'bg-emerald-500'
                    : runStatus === 'running'
                      ? 'bg-amber-500'
                      : 'bg-slate-300',
                ].join(' ')}
              />
              <p
                className={[
                  'text-sm font-semibold',
                  active ? 'text-slate-900' : 'text-slate-500',
                ].join(' ')}
              >
                {'Test ' + splitName(test.name)}
              </p>
            </button>
          );
        })}
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-6 grid-rows-1 overflow-hidden">
        <div className="relative col-span-4 h-full min-h-0 flex-1 overflow-hidden rounded-none bg-white">
          <MasDiagram
            workflow={workflow}
            agentStatus={selectedAgentStatus}
            activeHandoffEdges={selectedHandoffEdges}
            boundaryEdgeHighlights={selectedBoundaryHighlights}
          />
          <div className="absolute bottom-3 left-3 z-10 ">
            <div className="flex items-end gap-3 rounded-lg border border-slate-200 bg-white/95 px-3 py-2 backdrop-blur">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Start Test Cases
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                  <span className="font-semibold text-slate-900">
                    {selectedTestCaseIds.length} {selectedTestCaseIds.length === 1 ? 'test' : 'tests'}
                  </span>
                  <span>•</span>
                  <span>
                    {Object.values(testCaseRunStatuses).filter((status) => status === 'completed').length} ran
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <div className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1">
                    <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-500">To Run</p>
                    <p className="text-[11px] font-semibold text-slate-900">{selectedTestCaseIds.length - Object.values(testCaseRunStatuses).filter((status) => status === 'completed').length}</p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1">
                    <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-500">Passed</p>
                    <p className="text-[11px] font-semibold text-slate-900">—</p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1">
                    <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-500">Failed</p>
                    <p className="text-[11px] font-semibold text-slate-900">—</p>
                  </div>
                </div>
                {masTestRunId ? (
                  <p className="mt-1 truncate text-[10px] text-slate-500">Run: {masTestRunId}</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => {
                  void startSelectedTests();
                }}
                disabled={selectedTestCaseIds.length === 0 || startingTests}
                className={[
                  'inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-sm font-semibold transition',
                  selectedTestCaseIds.length === 0 || startingTests
                    ? 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400'
                    : 'cursor-pointer border-PrimaryBlue/20 bg-PrimaryBlue text-white hover:bg-PrimaryBlue/90',
                ].join(' ')}
              >
                {startingTests ? 'Starting…' : 'Start Tests'}
              </button>
            </div>
          </div>
        </div>
        <div className="col-span-2 flex h-full min-h-0 flex-col border-l border-slate-200 bg-white p-0">
          <div className="flex shrink-0 flex-row items-start p-0">
            {testCaseTabs.map((tab) => {
              const active = activeTab === tab.key;

              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={[
                    'flex h-full cursor-pointer min-w-36 py-2 items-center border-r border-b border-slate-200 px-4 text-left transition-colors',
                    active ? 'bg-slate-50' : 'bg-white hover:bg-slate-50',
                  ].join(' ')}
                >
                  <p
                    className={[
                      'text-sm font-semibold',
                      active ? 'text-slate-900' : 'text-slate-500',
                    ].join(' ')}
                  >
                    {tab.label}
                  </p>
                </button>
              );
            })}
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            {activeTab === 'test_case' ? (
              selectedTestCase ? (
                <div className="h-full min-h-0 overflow-auto p-4">
                  <div className="space-y-4">
                  <section className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Test Case
                        </p>
                        <p className="mt-1 text-base font-semibold text-slate-900">
                          {selectedTestCase.name}
                        </p>
                      </div>
                      <div
                        className={[
                          'rounded-full border px-3 py-1 text-xs font-semibold',
                          selectedTestCase.enabled
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : 'border-slate-200 bg-slate-50 text-slate-600',
                        ].join(' ')}
                      >
                        {selectedTestCase.enabled ? 'Enabled' : 'Disabled'}
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                          Created At
                        </p>
                        <p className="mt-1 text-sm text-slate-700">
                          {formatDateTime(selectedTestCase.createdAt)}
                        </p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                          Updated At
                        </p>
                        <p className="mt-1 text-sm text-slate-700">
                          {formatDateTime(selectedTestCase.updatedAt)}
                        </p>
                      </div>
                    </div>
                  </section>

                  <details className="rounded-2xl border border-slate-200 bg-white p-4" open>
                    <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
                      Input JSON
                    </summary>
                    <div className="mt-3 max-h-[min(22rem,40vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <JsonInspector value={selectedTestCase.inputJson} />
                    </div>
                  </details>

                  <details className="rounded-2xl border border-slate-200 bg-white p-4" open>
                    <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
                      Expected JSON
                    </summary>
                    <div className="mt-3 max-h-[min(22rem,40vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <JsonInspector value={selectedTestCase.expectedJson} />
                    </div>
                  </details>
                  </div>
                </div>
              ) : (
                <div className="p-4">
                  <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
                    <p className="text-sm font-semibold text-slate-900">No test case selected.</p>
                  </div>
                </div>
              )
            ) : activeTab === 'traces' ? (
              selectedTestCase ? (
                selectedTraceRun ? (
                  <div className="h-full min-h-0 overflow-hidden p-0">
                    <MasTracesTab
                      agentNames={workflow.participating_agents}
                      eventsStreamUrl={selectedTraceRun.eventsStreamUrl}
                      swarm_run_id={selectedTraceRun.swarmRunId}
                      setAgentStatus={(value) => {
                        setTestCaseAgentStatuses((prev) => {
                          const current =
                            prev[selectedTestCase.id] ?? buildInitialAgentStatus(workflow.participating_agents);
                          const nextValue =
                            typeof value === 'function' ? value(current) : value;
                          return {
                            ...prev,
                            [selectedTestCase.id]: nextValue,
                          };
                        });
                      }}
                      setActiveHandoffEdges={(value) => {
                        setTestCaseHandoffEdges((prev) => {
                          const current = prev[selectedTestCase.id] ?? {};
                          const nextValue =
                            typeof value === 'function' ? value(current) : value;
                          return {
                            ...prev,
                            [selectedTestCase.id]: nextValue,
                          };
                        });
                      }}
                      setBoundaryEdgeHighlights={(value) => {
                        setTestCaseBoundaryHighlights((prev) => {
                          const current = prev[selectedTestCase.id] ?? { start: 'idle', end: 'idle' };
                          const nextValue =
                            typeof value === 'function' ? value(current) : value;
                          return {
                            ...prev,
                            [selectedTestCase.id]: nextValue,
                          };
                        });
                      }}
                      onMasDone={async () => {
                        await handleMasDone(selectedTestCase.id, selectedTraceRun.swarmRunId);
                      }}
                    />
                  </div>
                ) : (
                  <div className="p-4">
                    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
                      <p className="text-sm font-semibold text-slate-900">No trace stream yet</p>
                      <p className="mt-2 text-sm text-slate-500">
                        Start tests and bind the selected case to a swarm run stream to view traces here.
                      </p>
                    </div>
                  </div>
                )
              ) : (
                <div className="p-4">
                  <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
                    <p className="text-sm font-semibold text-slate-900">No test case selected.</p>
                  </div>
                </div>
              )
            ) : activeTab === 'output' ? (
              <div className="h-full min-h-0 overflow-auto">
                <MasResultsTab input={selectedTestCase?.inputJson ?? {}} output={selectedTestCaseOutput} />
              </div>
            ) : (
              <div className="h-full min-h-0 overflow-auto ">
                <MasMetricsTab metrics={selectedTestCaseMetrics} />
              </div>
            )}
          </div>
        </div>
      </div>
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
