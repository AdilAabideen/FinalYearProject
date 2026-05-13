import { AgentModelSelect } from '../shared/AgentModelSelect';
import { CaseBadge } from './CaseBadge';
import { StatusDot } from './StatusDot';
import { titleCaseKey } from '../../utils/format';
import { AgentTestCaseViewerPanel } from './AgentTestCaseViewerPanel';

type ViewerTabKey = 'case_details' | 'test_traces' | 'outputs' | 'diff' | 'metrics';
type CaseStatus = 'pending' | 'running' | 'passed' | 'failed';

type AgentTestHarnessPanelProps = {
  viewerTabsId: string;
  viewerTabs: Array<{ key: ViewerTabKey; label: string }>;
  activeViewerTab: ViewerTabKey;
  onChangeViewerTab: (tab: ViewerTabKey) => void;
  viewerTabId: (key: ViewerTabKey) => string;
  viewerPanelId: (key: ViewerTabKey) => string;
  selectedCases: Array<{ id: string; name: string; inputJson: Record<string, unknown> }>;
  activeCaseId: string | null;
  setActiveCaseId: (id: string) => void;
  caseStates: Record<string, { status: CaseStatus }>;
  selectedCaseCount: number;
  totals: { total: number; completed: number; running: number; queued: number };
  modelSelectId: string;
  models: Parameters<typeof AgentModelSelect>[0]['models'];
  modelsStatus: Parameters<typeof AgentModelSelect>[0]['modelsStatus'];
  selectedModelId: string;
  setSelectedModelId: (value: string) => void;
  runPhase: 'idle' | 'running' | 'done';
  onStart: (modelId?: string) => void | Promise<void>;
  activeCase: { id: string; name: string; inputJson: Record<string, unknown> } | null;
  activeAgentRunId: string | null;
  activeOutputState?: AgentTestCaseViewerPanelProps['activeOutputState'];
  activeMetricsState?: AgentTestCaseViewerPanelProps['activeMetricsState'];
  activeDiffState?: AgentTestCaseViewerPanelProps['activeDiffState'];
  activeCaseStatus?: CaseStatus;
  activeResultView: AgentTestCaseViewerPanelProps['activeResultView'];
  activeAdditionalOutputEntries: AgentTestCaseViewerPanelProps['activeAdditionalOutputEntries'];
  activeReliabilitySummaryView: AgentTestCaseViewerPanelProps['activeReliabilitySummaryView'];
  diffRenderer: AgentTestCaseViewerPanelProps['diffRenderer'];
  handleRetryOutput: () => void;
};

type AgentTestCaseViewerPanelProps = Parameters<typeof AgentTestCaseViewerPanel>[0];

// Renders the agent test harness panel.
export function AgentTestHarnessPanel({
  viewerTabsId,
  viewerTabs,
  activeViewerTab,
  onChangeViewerTab,
  viewerTabId,
  viewerPanelId,
  selectedCases,
  activeCaseId,
  setActiveCaseId,
  caseStates,
  selectedCaseCount,
  totals,
  modelSelectId,
  models,
  modelsStatus,
  selectedModelId,
  setSelectedModelId,
  runPhase,
  onStart,
  activeCase,
  activeAgentRunId,
  activeOutputState,
  activeMetricsState,
  activeDiffState,
  activeCaseStatus,
  activeResultView,
  activeAdditionalOutputEntries,
  activeReliabilitySummaryView,
  diffRenderer,
  handleRetryOutput,
}: AgentTestHarnessPanelProps) {
  return (
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
                  className={`flex w-full items-center justify-between p-4 text-left transition ${isActive ? 'bg-slate-50' : 'hover:bg-slate-50'}`}
                >
                  <div className="min-w-0 space-y-1">
                    <p className="truncate text-sm font-semibold text-slate-900">{titleCaseKey(testCase.name)}</p>
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
              {selectedCaseCount} case{selectedCaseCount === 1 ? '' : 's'} selected
            </p>

            <div className="mt-3 flex items-center gap-2">
              <AgentModelSelect
                id={modelSelectId}
                models={models}
                modelsStatus={modelsStatus}
                selectedModelId={selectedModelId}
                setSelectedModelId={setSelectedModelId}
                disabled={runPhase === 'running'}
                selectClassName="min-w-52 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
              />
            </div>
          </div>

          <button
            type="button"
            onClick={() => onStart(selectedModelId || undefined)}
            disabled={runPhase === 'running' || !selectedCases.length}
            className={`inline-flex items-center gap-2 rounded-2xl px-5 py-2 text-xs font-semibold shadow-slate-900/40 backdrop-blur transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-white ${runPhase === 'running' ? 'cursor-not-allowed bg-slate-200 text-slate-600' : 'bg-PrimaryBlue text-white hover:scale-[1.02] hover:bg-PrimaryBlue/90 disabled:cursor-not-allowed disabled:opacity-60'}`}
          >
            <span>{runPhase === 'running' ? 'Running' : runPhase === 'done' ? 'Re Run' : 'Start'}</span>
            <span className={`inline-flex h-2.5 w-2.5 rounded-full ${runPhase === 'running' ? 'bg-orange-400' : 'bg-emerald-400'}`} />
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
        <AgentTestCaseViewerPanel
          viewerTabsId={viewerTabsId}
          viewerTabs={viewerTabs}
          activeViewerTab={activeViewerTab}
          onChangeViewerTab={onChangeViewerTab}
          viewerTabId={viewerTabId}
          viewerPanelId={viewerPanelId}
          activeCase={activeCase}
          activeCaseId={activeCaseId}
          activeAgentRunId={activeAgentRunId}
          runPhase={runPhase}
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
    </div>
  );
}
