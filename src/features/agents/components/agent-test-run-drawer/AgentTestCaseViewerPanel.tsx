import { SegmentedTabs } from '../../../../shared/ui/SegmentedTabs';
import { Badge } from '../../../../shared/ui/Badge';
import { AgentTracesComponent } from '../AgentTracesComponent';
import { AgentDecisionSummaryCards } from '../shared/AgentDecisionSummaryCards';
import { AgentNarrativeSections } from '../shared/AgentNarrativeSections';
import { AgentAdditionalOutputFields } from '../shared/AgentAdditionalOutputFields';
import { AgentRawJsonDetails } from '../shared/AgentRawJsonDetails';
import { AgentReliabilitySummaryPanel } from '../shared/AgentReliabilitySummaryPanel';
import { AgentStatCard as StatCard } from '../shared/AgentStatCard';
import { CaseBadge } from './CaseBadge';
import { formatCurrency, formatDuration, formatInteger } from '../../utils/format';
import { asNumber, isRecord, type ResultViewModel } from '../../utils/runResult';
import type { ReliabilitySummaryView } from '../../utils/reliability';

type ViewerTabKey = 'case_details' | 'test_traces' | 'outputs' | 'diff' | 'metrics';

type AgentTestCaseViewerPanelProps = {
  viewerTabsId: string;
  viewerTabs: Array<{ key: ViewerTabKey; label: string }>;
  activeViewerTab: ViewerTabKey;
  onChangeViewerTab: (tab: ViewerTabKey) => void;
  viewerTabId: (key: ViewerTabKey) => string;
  viewerPanelId: (key: ViewerTabKey) => string;
  activeCase: { id: string; name: string; inputJson: Record<string, unknown> } | null;
  activeCaseId: string | null;
  activeAgentRunId: string | null;
  runPhase: 'idle' | 'running' | 'done';
  activeOutputState?: {
    status: 'idle' | 'loading' | 'ready' | 'error';
    agentRunId?: string;
    output?: Record<string, unknown> | null;
    error?: string;
  };
  activeMetricsState?: {
    status: 'idle' | 'loading' | 'ready' | 'error';
    agentRunId?: string;
    metrics?: Record<string, unknown> | null;
    error?: string;
  };
  activeDiffState?: {
    status: 'idle' | 'loading' | 'ready' | 'error';
    agentRunId?: string;
    diff?: Record<string, unknown> | null;
    error?: string;
  };
  activeCaseStatus?: 'pending' | 'running' | 'passed' | 'failed';
  activeResultView: ResultViewModel | null;
  activeAdditionalOutputEntries: Array<[string, unknown]>;
  activeReliabilitySummaryView: ReliabilitySummaryView;
  diffRenderer: (diff: Record<string, unknown>) => React.ReactNode;
  handleRetryOutput: () => void;
};

// Renders the agent test case viewer.
export function AgentTestCaseViewerPanel({
  viewerTabsId,
  viewerTabs,
  activeViewerTab,
  onChangeViewerTab,
  viewerTabId,
  viewerPanelId,
  activeCase,
  activeCaseId,
  activeAgentRunId,
  runPhase,
  activeOutputState,
  activeMetricsState,
  activeDiffState,
  activeCaseStatus,
  activeResultView,
  activeAdditionalOutputEntries,
  activeReliabilitySummaryView,
  diffRenderer,
  handleRetryOutput,
}: AgentTestCaseViewerPanelProps) {
  const activeOutputRecord =
    activeOutputState?.status === 'ready' && isRecord(activeOutputState.output) ? activeOutputState.output : null;
  const activeMetricsRecord =
    activeMetricsState?.status === 'ready' && isRecord(activeMetricsState.metrics)
      ? activeMetricsState.metrics
      : null;
  const activeDiffRecord =
    activeDiffState?.status === 'ready' && isRecord(activeDiffState.diff) ? activeDiffState.diff : null;

  return (
    <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-white p-3">
      <SegmentedTabs
        idBase={viewerTabsId}
        tabs={viewerTabs}
        value={activeViewerTab}
        onChange={onChangeViewerTab}
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
            <p className="text-xs font-semibold text-slate-900">Details</p>
            {activeCase ? (
              <div className="mt-2 space-y-2">
                <p className="text-sm font-semibold text-slate-900">{activeCase.name}</p>
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
          <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-slate-50">
            <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-100 bg-slate-50 p-3">
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
          className="h-full min-h-0 overflow-auto"
        >
          <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-slate-50 p-3">
            {!activeCaseId ? (
              <p className="text-xs text-slate-600">Select a test case to view its output.</p>
            ) : activeOutputState?.status === 'loading' ? (
              <p className="text-xs text-slate-600">Loading output…</p>
            ) : activeOutputState?.status === 'error' ? (
              <div className="space-y-3">
                <p className="text-xs text-rose-700">{activeOutputState.error ?? 'Failed to load output.'}</p>
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
              activeOutputRecord && activeResultView ? (
                <div className="space-y-4 pb-2">
                  <section className="rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,rgba(14,165,233,0.06)_0%,rgba(255,255,255,0.95)_42%,rgba(16,185,129,0.06)_100%)] p-4">
                    <AgentDecisionSummaryCards
                      decisionLabel={activeResultView.decisionLabel}
                      decisionTone={activeResultView.decisionTone}
                      confidenceLabel={activeResultView.confidenceLabel}
                    />
                  </section>

                  <AgentNarrativeSections
                    caseSummary={activeResultView.caseSummary}
                    justification={activeResultView.justification}
                    risks={activeResultView.risks}
                    missingInformation={activeResultView.missingInformation}
                  />

                  <AgentAdditionalOutputFields entries={activeAdditionalOutputEntries} />
                  <AgentRawJsonDetails summary="Raw Output JSON" value={activeOutputRecord} />
                </div>
              ) : (
                <p className="text-xs text-slate-600">No output returned for this case.</p>
              )
            ) : activeCaseStatus === 'passed' || activeCaseStatus === 'failed' ? (
              <p className="text-xs text-slate-600">
                Output not available yet for this case. You can retry fetching it.
              </p>
            ) : (
              <p className="text-xs text-slate-600">Output will appear once this case finishes running.</p>
            )}
          </div>
        </div>

        <div
          id={viewerPanelId('diff')}
          role="tabpanel"
          aria-labelledby={viewerTabId('diff')}
          hidden={activeViewerTab !== 'diff'}
          className="h-full min-h-0 overflow-auto"
        >
          {!activeCaseId ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
              Select a test case to view its diff.
            </div>
          ) : activeDiffState?.status === 'loading' ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
              Loading diff…
            </div>
          ) : activeDiffState?.status === 'error' ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
              {activeDiffState.error}
            </div>
          ) : activeDiffState?.status === 'ready' && activeDiffRecord ? (
            diffRenderer(activeDiffRecord)
          ) : activeCaseStatus === 'passed' || activeCaseStatus === 'failed' ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
              Diff not available for this case.
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
              Diff will appear once this case finishes running.
            </div>
          )}
        </div>

        <div
          id={viewerPanelId('metrics')}
          role="tabpanel"
          aria-labelledby={viewerTabId('metrics')}
          hidden={activeViewerTab !== 'metrics'}
          className="h-full min-h-0 overflow-auto"
        >
          {activeMetricsState?.status === 'loading' ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
              Loading metrics…
            </div>
          ) : activeMetricsState?.status === 'error' ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
              {activeMetricsState.error}
            </div>
          ) : activeMetricsState?.status === 'ready' ? (
            <div className="space-y-4 pb-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <h4 className="text-sm font-semibold text-slate-900">Metrics</h4>
                  <Badge className="bg-white text-slate-700 ring-slate-200">
                    {activeCaseStatus ? `Case: ${activeCaseStatus}` : 'Case status unavailable'}
                  </Badge>
                </div>

                <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <StatCard label="LLM Calls" value={formatInteger(asNumber(activeMetricsRecord?.llm_call_count))} tone="accent" />
                  <StatCard label="Tool Calls" value={formatInteger(asNumber(activeMetricsRecord?.tool_call_count))} />
                  <StatCard label="Input Tokens" value={formatInteger(asNumber(activeMetricsRecord?.input_tokens_total))} />
                  <StatCard label="Output Tokens" value={formatInteger(asNumber(activeMetricsRecord?.output_tokens_total))} />
                  <StatCard label="Total Tokens" value={formatInteger(asNumber(activeMetricsRecord?.tokens_total))} />
                  <StatCard label="Duration" value={formatDuration(asNumber(activeMetricsRecord?.duration_seconds))} />
                  <StatCard label="Cost" value={formatCurrency(asNumber(activeMetricsRecord?.cost_usd_total))} />
                  <StatCard
                    label="Failure Reason"
                    value={
                      typeof activeMetricsRecord?.failure_reason === 'string' &&
                      activeMetricsRecord.failure_reason.trim().length > 0
                        ? activeMetricsRecord.failure_reason
                        : 'None'
                    }
                    tone={
                      typeof activeMetricsRecord?.failure_reason === 'string' &&
                      activeMetricsRecord.failure_reason.trim().length > 0
                        ? 'danger'
                        : 'positive'
                    }
                    small={true}
                  />
                </div>

                <AgentReliabilitySummaryPanel summaryView={activeReliabilitySummaryView} statusSmall={true} />

                <AgentRawJsonDetails
                  summary="Raw Metrics JSON"
                  value={activeMetricsState.metrics}
                  className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3"
                  contentClassName="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-white p-3"
                />
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
