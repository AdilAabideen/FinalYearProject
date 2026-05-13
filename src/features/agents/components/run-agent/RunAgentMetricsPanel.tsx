import { formatCurrency, formatDuration, formatInteger } from '../../utils/format';
import { AgentRawJsonDetails } from '../shared/AgentRawJsonDetails';
import { AgentReliabilitySummaryPanel } from '../shared/AgentReliabilitySummaryPanel';
import { AgentStatCard } from '../shared/AgentStatCard';
import type { AgentRunMetrics } from '../../../../types/agentRuns';
import type { ReliabilitySummaryView } from '../../utils/reliability';

type RunAgentMetricsPanelProps = {
  runMetrics: AgentRunMetrics | null;
  resultsLoading: boolean;
  reliabilitySummaryView: ReliabilitySummaryView;
};

// Renders the run agent metrics panel.
export function RunAgentMetricsPanel({
  runMetrics,
  resultsLoading,
  reliabilitySummaryView,
}: RunAgentMetricsPanelProps) {
  if (!runMetrics) return null;

  return (
    <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-900">Metrics</h4>
        {resultsLoading ? (
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
            Loading…
          </span>
        ) : null}
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <AgentStatCard label="LLM Calls" value={formatInteger(runMetrics.llm_call_count ?? null)} tone="accent" />
        <AgentStatCard label="Tool Calls" value={formatInteger(runMetrics.tool_call_count ?? null)} />
        <AgentStatCard label="Input Tokens" value={formatInteger(runMetrics.input_tokens_total ?? null)} />
        <AgentStatCard label="Output Tokens" value={formatInteger(runMetrics.output_tokens_total ?? null)} />
        <AgentStatCard label="Total Tokens" value={formatInteger(runMetrics.tokens_total ?? null)} />
        <AgentStatCard label="Duration" value={formatDuration(runMetrics.duration_seconds ?? null)} />
        <AgentStatCard label="Cost" value={formatCurrency(runMetrics.cost_usd_total ?? null)} />
        <AgentStatCard
          label="Failure Reason"
          value={runMetrics.failure_reason || 'None'}
          tone={runMetrics.failure_reason ? 'danger' : 'positive'}
        />
      </div>

      <AgentReliabilitySummaryPanel summaryView={reliabilitySummaryView} />
      <AgentRawJsonDetails
        summary="Raw Metrics JSON"
        value={runMetrics}
        className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3"
        contentClassName="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-white p-3"
      />
    </div>
  );
}
