import { JsonInspector } from '../../../../shared/ui/JsonInspector';
import { Badge } from '../../../../shared/ui/Badge';
import { AgentStatCard as StatCard } from '../shared/AgentStatCard';
import { formatCurrency, formatInteger, formatLatencyMs, formatPercent, titleCaseKey } from '../../utils/format';

type AggregatedRunMetricsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: import('../../../../types/agentTests').AgentTestRunBatchMetricsRead };

type AggregatedSummary = import('../../../../types/agentTests').AgentTestRunBatchMetricsRead['summary'];

type AgentTestRunMetricsPanelProps = {
  runId: string | null;
  aggregatedRunMetricsState: AggregatedRunMetricsState;
  aggregatedRunMetrics: import('../../../../types/agentTests').AgentTestRunBatchMetricsRead | null;
  aggregatedSummary: AggregatedSummary | null;
  aggregatedFailureReasonEntries: Array<[string, number]>;
  onRetry: () => void;
};

// Renders the agent test run metrics.
export function AgentTestRunMetricsPanel({
  runId,
  aggregatedRunMetricsState,
  aggregatedRunMetrics,
  aggregatedSummary,
  aggregatedFailureReasonEntries,
  onRetry,
}: AgentTestRunMetricsPanelProps) {
  if (!runId) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        Start a test run to view aggregated run metrics.
      </div>
    );
  }

  if (aggregatedRunMetricsState.status === 'loading') {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        Loading run metrics…
      </div>
    );
  }

  if (aggregatedRunMetricsState.status === 'error') {
    return (
      <div className="space-y-3 rounded-2xl border border-rose-200 bg-rose-50 p-4">
        <p className="text-sm text-rose-700">{aggregatedRunMetricsState.error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center justify-center rounded-xl border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-700 transition hover:bg-rose-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!aggregatedRunMetrics) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        Run metrics not available yet.
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-3">
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Aggregated Run Summary</p>
            <p className="mt-1 text-sm text-slate-700">Summary-level metrics across case runs for this test run.</p>
          </div>
          <Badge className="bg-white text-slate-700 ring-slate-200">
            Success Rate: {formatPercent(aggregatedSummary?.successRate ?? null, 2)}
          </Badge>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <StatCard label="Average Cost" value={formatCurrency(aggregatedSummary?.costUsdAvg ?? null)} tone="accent" />
          <StatCard label="Total Cost" value={formatCurrency(aggregatedSummary?.costUsdTotal ?? null)} tone="accent" />
          <StatCard label="Average Duration (ms)" value={formatLatencyMs(aggregatedSummary?.durationMsAvg ?? null)} />
          <StatCard label="Failed Runs" value={formatInteger(aggregatedSummary?.failedRuns ?? null)} tone={(aggregatedSummary?.failedRuns ?? 0) > 0 ? 'danger' : 'default'} />
          <StatCard label="LLM Calls (Avg)" value={formatInteger(aggregatedSummary?.llmCallCountAvg ?? null)} />
          <StatCard label="LLM Calls (Total)" value={formatInteger(aggregatedSummary?.llmCallCountTotal ?? null)} />
          <StatCard label="Tool Calls (Avg)" value={formatInteger(aggregatedSummary?.toolCallCountAvg ?? null)} />
          <StatCard label="Tool Calls (Total)" value={formatInteger(aggregatedSummary?.toolCallCountTotal ?? null)} />
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Input Tokens (Avg)" value={formatInteger(aggregatedSummary?.inputTokensAvg ?? null)} />
          <StatCard label="Input Tokens (Total)" value={formatInteger(aggregatedSummary?.inputTokensTotal ?? null)} />
          <StatCard label="Output Tokens (Avg)" value={formatInteger(aggregatedSummary?.outputTokensAvg ?? null)} />
          <StatCard label="Output Tokens (Total)" value={formatInteger(aggregatedSummary?.outputTokensTotal ?? null)} />
          <StatCard label="Tokens (Avg)" value={formatInteger(aggregatedSummary?.tokensAvg ?? null)} />
          <StatCard label="Tokens (Total)" value={formatInteger(aggregatedSummary?.tokensTotal ?? null)} />
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Failure Reason Issues</p>
        {aggregatedFailureReasonEntries.length ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {aggregatedFailureReasonEntries.map(([reason, count]) => (
              <StatCard key={reason} label={titleCaseKey(reason)} value={formatInteger(count)} tone={count > 0 ? 'danger' : 'default'} />
            ))}
          </div>
        ) : (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard label="Failure Reason Issues" value="None detected" tone="positive" />
          </div>
        )}
      </section>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">Raw Summary JSON</summary>
        <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <JsonInspector value={aggregatedSummary} />
        </div>
      </details>
    </div>
  );
}
