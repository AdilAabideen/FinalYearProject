import { useCallback, useId } from 'react';
import type { MasCatalogDetail } from '../../../types/mas';
import { MasDiagram } from './MasDiagram';
import { MasSelectedCaseTabs } from './MasSelectedCaseTabs';
import { MasTabs } from './MasTabs';
import { MasTestRunOverlayCard } from './MasTestRunOverlayCard';
import { MasTestCaseWorkspacePanel } from './MasTestCaseWorkspacePanel';
import { MasTestCaseSelectionPanel } from './MasTestCaseSelectionPanel';
import { MasTestCaseDetailsPanel } from './MasTestCaseDetailsPanel';
import { MasTestCaseTracesPanel } from './MasTestCaseTracesPanel';
import { MasTestCaseDiffPanel } from './MasTestCaseDiffPanel';
import { MasBatchOutputPanel } from './MasBatchOutputPanel';
import { MasBatchMetricsPanel } from './MasBatchMetricsPanel';
import MasResultsTab from './MasResultsTab';
import MasMetricsTab from './MasMetricsTab';
import { useMasBatchMetrics } from '../hooks/useMasBatchMetrics';
import { useMasBatchResults } from '../hooks/useMasBatchResults';
import { useMasCaseCompletionData } from '../hooks/useMasCaseCompletionData';
import { useMasCaseVisualizationState } from '../hooks/useMasCaseVisualizationState';
import { useMasTestCaseCatalog } from '../hooks/useMasTestCaseCatalog';
import { useMasTestCaseSelection } from '../hooks/useMasTestCaseSelection';
import { useMasTestRunStream } from '../hooks/useMasTestRunStream';
import { useModels } from '../../agents/hooks/useModels';
import {
  getActualFinalEsiLevelFromDiff,
  getExpectedAcuityFromDiff,
  summarizeRunStatuses,
  type MasTestTabKey,
  type TestCaseTabKey,
} from '../utils/masTestCases';

type MasTestCasesProps = {
  workflow: MasCatalogDetail;
};

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

export default function MasTestCases({ workflow }: MasTestCasesProps) {
  const { testCases, loading } = useMasTestCaseCatalog(workflow?.metadata.workflow_id);
  const {
    selectedTestCase,
    setSelectedTestCase,
    selectedTestCaseId,
    selectedTestCaseIds,
    showCaseWorkspace,
    activeTab,
    activeMasTab,
    visibleTestCases,
    allSelected,
    setActiveTab,
    setActiveMasTab,
    toggleTestCaseSelection,
    toggleSelectAllTestCases,
    openSelectedCases,
  } = useMasTestCaseSelection(testCases);
  const {
    masRunResultsState,
    masRunResults,
    fetchMasRunResults,
    resetMasRunResults,
  } = useMasBatchResults();
  const {
    masRunMetricsState,
    masRunMetrics,
    fetchMasRunMetrics,
    resetMasRunMetrics,
  } = useMasBatchMetrics();
  const {
    testCaseOutputs,
    testCaseMetrics,
    handleMasDone,
    resetCaseCompletionData,
  } = useMasCaseCompletionData();
  const {
    selectedAgentStatus,
    selectedHandoffEdges,
    selectedBoundaryHighlights,
    updateSelectedAgentStatus,
    updateSelectedHandoffEdges,
    updateSelectedBoundaryHighlights,
    initializeCaseVisualState,
    resetVisualizationState,
  } = useMasCaseVisualizationState(workflow.participating_agents, selectedTestCaseId);

  const handleStartReset = useCallback(() => {
    resetCaseCompletionData();
    resetVisualizationState();
    resetMasRunResults();
    resetMasRunMetrics();
  }, [resetCaseCompletionData, resetMasRunMetrics, resetMasRunResults, resetVisualizationState]);

  const handleRunDone = useCallback(
    (runId: string) => {
      void fetchMasRunResults(runId);
      void fetchMasRunMetrics(runId);
    },
    [fetchMasRunMetrics, fetchMasRunResults],
  );

  const { models, status: modelsStatus, selectedModelId, setSelectedModelId } = useModels();
  const modelSelectId = useId();

  const {
    masTestRunId,
    startingTests,
    testCaseTraceRuns,
    testCaseRunStatuses,
    testCaseDiffs,
    startSelectedTests,
  } = useMasTestRunStream({
    workflowId: workflow.metadata.workflow_id,
    selectedTestCaseIds,
    model_id: selectedModelId,
    onStartReset: handleStartReset,
    onCaseBoundToSwarmRun: initializeCaseVisualState,
    onRunDone: handleRunDone,
  });

  const selectedTraceRun = selectedTestCaseId ? testCaseTraceRuns[selectedTestCaseId] ?? null : null;
  const selectedTestCaseStatus = selectedTestCaseId ? testCaseRunStatuses[selectedTestCaseId] ?? 'idle' : 'idle';
  const selectedTestCaseDiffState = selectedTestCaseId ? testCaseDiffs[selectedTestCaseId] : undefined;
  const selectedTestCaseOutput = selectedTestCaseId ? testCaseOutputs[selectedTestCaseId] ?? null : null;
  const selectedTestCaseMetrics = selectedTestCaseId ? testCaseMetrics[selectedTestCaseId] ?? null : null;
  const expectedAcuity = getExpectedAcuityFromDiff(selectedTestCaseDiffState);
  const actualFinalEsiLevel = getActualFinalEsiLevelFromDiff(selectedTestCaseDiffState);
  const { ranCount, passedCount, failedCount, toRunCount } = summarizeRunStatuses(
    testCaseRunStatuses,
    selectedTestCaseIds.length,
  );

  const handleSelectedMasDone = useCallback(async () => {
    if (!selectedTestCaseId || !selectedTraceRun) return;
    await handleMasDone(selectedTestCaseId, selectedTraceRun.swarmRunId);
  }, [handleMasDone, selectedTestCaseId, selectedTraceRun]);

  const handleStartTests = useCallback(() => {
    setActiveTab('traces');
    void startSelectedTests();
  }, [setActiveTab, startSelectedTests]);

  if (loading) {
    return (
      <div className="flex h-full min-h-[560px] flex-1 items-center justify-center bg-white p-6">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-6 py-8 text-center shadow-sm">
          <p className="text-sm font-semibold text-slate-900">Loading test cases…</p>
        </div>
      </div>
    );
  }

  if (testCases.length === 0) {
    return (
      <div className="flex h-full min-h-[560px] flex-1 items-center justify-center bg-white p-6">
        <div className="flex items-stretch border-b border-slate-200 bg-white">No tests</div>
      </div>
    );
  }

  if (!showCaseWorkspace) {
    return (
      <MasTestCaseSelectionPanel
        testCases={testCases}
        selectedTestCaseIds={selectedTestCaseIds}
        allSelected={allSelected}
        onToggleAll={toggleSelectAllTestCases}
        onToggleOne={toggleTestCaseSelection}
        onOpenSelectedCases={openSelectedCases}
        modelSelectId={modelSelectId}
        modelsStatus={modelsStatus}
        models={models}
        selectedModelId={selectedModelId}
        setSelectedModelId={setSelectedModelId}
      />
    );
  }

  if (visibleTestCases.length === 0) {
    return (
      <div className="flex h-full min-h-[560px] flex-1 items-center justify-center bg-white p-6">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-6 py-8 text-center shadow-sm">
          <p className="text-sm font-semibold text-slate-900">No selected test cases</p>
          <p className="mt-2 text-sm text-slate-500">
            Go back and choose at least one test case to open the workspace.
          </p>
        </div>
      </div>
    );
  }

  return (
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
                onStartTests={handleStartTests}
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
  );
}
