import { Badge } from '../../../shared/ui/Badge';
import { AgentStatCard as StatCard } from '../../agents/components/shared/AgentStatCard';
import { AgentRawJsonDetails } from '../../agents/components/shared/AgentRawJsonDetails';
import { AgentReliabilitySummaryPanel } from '../../agents/components/shared/AgentReliabilitySummaryPanel';
import { formatCurrency, formatDuration, formatInteger } from '../../agents/utils/format';
import { asNumber } from '../../agents/utils/runResult';
import { getReliabilitySummaryView } from '../../agents/utils/reliability';
import type { MetricsState } from '../utils/masTraces';

type MasTracesMetricsPanelProps = {
  activeMetricsState: MetricsState;
};

// Renders the MAS traces metrics panel.
export function MasTracesMetricsPanel({ activeMetricsState }: MasTracesMetricsPanelProps) {
  const activeMetricsRecord = activeMetricsState.status === 'ready' ? activeMetricsState.metrics : null;
  const activeReliabilitySummaryView = getReliabilitySummaryView(activeMetricsRecord, {
    fallbackCountsToZero: true,
  });
  const activeCaseStatus = activeMetricsRecord?.status ?? null;

  if (activeMetricsState.status === 'loading') {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        Loading metrics…
      </div>
    );
  }

  if (activeMetricsState.status === 'error') {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        {activeMetricsState.error}
      </div>
    );
  }

  if (activeMetricsState.status !== 'ready') {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        Metrics will appear once this agent finishes running.
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-2">
      <div className="border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-slate-900">Metrics</h4>
          <Badge className="bg-white text-slate-700 ring-slate-200">
            {activeCaseStatus ? `Case: ${activeCaseStatus}` : 'Case status unavailable'}
          </Badge>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            label="LLM Calls"
            value={formatInteger(asNumber(activeMetricsRecord?.llm_call_count))}
            tone="accent"
          />
          <StatCard
            label="Tool Calls"
            value={formatInteger(asNumber(activeMetricsRecord?.tool_call_count))}
          />
          <StatCard
            label="Input Tokens"
            value={formatInteger(asNumber(activeMetricsRecord?.input_tokens_total))}
          />
          <StatCard
            label="Output Tokens"
            value={formatInteger(asNumber(activeMetricsRecord?.output_tokens_total))}
          />
          <StatCard
            label="Total Tokens"
            value={formatInteger(asNumber(activeMetricsRecord?.tokens_total))}
          />
          <StatCard
            label="Duration"
            value={formatDuration(asNumber(activeMetricsRecord?.duration_seconds))}
          />
          <StatCard
            label="Cost"
            value={formatCurrency(asNumber(activeMetricsRecord?.cost_usd_total))}
          />
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

        <AgentReliabilitySummaryPanel
          summaryView={activeReliabilitySummaryView}
          statusSmall={true}
        />

        <AgentRawJsonDetails
          summary="Raw Metrics JSON"
          value={activeMetricsState.metrics}
          className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3"
          contentClassName="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-white p-3"
        />
      </div>
    </div>
  );
}
