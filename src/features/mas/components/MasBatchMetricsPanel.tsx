import type { MasTestRunMetrics } from '../../../types/masTests';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { AgentStatCard as StatCard } from '../../agents/components/shared/AgentStatCard';
import { formatDuration, formatInteger, formatLatencyMs } from '../../agents/utils/format';

type MasBatchMetricsPanelProps = {
  status: 'idle' | 'loading' | 'error' | 'ready';
  error?: string;
  metrics: MasTestRunMetrics | null;
};

// Formats usd.
function formatUsd(value: number | null) {
  return value == null
    ? '—'
    : new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 4,
    }).format(value);
}

// Renders the MAS batch metrics panel.
export function MasBatchMetricsPanel({ status, error, metrics }: MasBatchMetricsPanelProps) {
  if (status === 'idle') {
    return (
      <div className=" bg-white p-4 text-md text-slate-700 ">
        <p className='text-xl font-semibold text-slate-900 mb-2  border-slate-200 '>MAS Test Metrics</p>
        Please Start and finish a MAS test run to view batch metrics.
      </div>
    );
  }

  if (status === 'loading') {
    return (
      <div className=" bg-white p-4 text-md text-slate-700 ">
        <p className='text-xl font-semibold text-slate-900 mb-2  border-slate-200 '>MAS Test Metrics</p>
        Please Start and finish a MAS test run to view batch metrics.
      </div>
    );
  }

  if (status === 'error') {
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>;
  }

  if (!metrics) return null;

  return (
    <div className="space-y-4 pb-3">
      <section className=" border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xl font-semibold text-slate-900">{metrics.run.name || 'MAS Test Run Metrics'}</p>
            <p className="mt-1 text-sm text-slate-700">Workflow: {metrics.run.workflowId}</p>
          </div>
          <div
            className={[
              'rounded-full border px-3 py-1 text-xs font-semibold',
              metrics.run.status.toLowerCase().includes('fail')
                ? 'border-rose-200 bg-rose-50 text-rose-700'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700',
            ].join(' ')}
          >
            {metrics.run.status.slice(0,1).toUpperCase() + metrics.run.status.slice(1)}
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <StatCard label="Total Cases" value={formatInteger(metrics.summary.totalCases)} tone="accent" />
          <StatCard
            label="Avg Duration"
            value={formatDuration(metrics.summary.durationMsAvg == null ? null : metrics.summary.durationMsAvg / 1000)}
          />
          <StatCard label="Total Cost" value={formatUsd(metrics.summary.costUsdTotal)} tone="accent" />
          <StatCard label="Avg Cost" value={formatUsd(metrics.summary.costUsdAvg)} tone="accent" />
          <StatCard label="LLM Calls (Total)" value={formatInteger(metrics.summary.llmCallCountTotal)} />
          <StatCard label="LLM Calls (Avg)" value={formatInteger(metrics.summary.llmCallCountAvg)} />
          <StatCard label="Tool Calls (Total)" value={formatInteger(metrics.summary.toolCallCountTotal)} />
          <StatCard label="Tool Calls (Avg)" value={formatInteger(metrics.summary.toolCallCountAvg)} />
          <StatCard label="Tokens (Total)" value={formatInteger(metrics.summary.tokensTotal)} />
          <StatCard label="Tokens (Avg)" value={formatInteger(metrics.summary.tokensAvg)} />
          <StatCard label="Input Tokens (Avg)" value={formatInteger(metrics.summary.inputTokensAvg)} />
          <StatCard label="Output Tokens (Avg)" value={formatInteger(metrics.summary.outputTokensAvg)} />
          <StatCard label="Agent Runs (Total)" value={formatInteger(metrics.summary.agentRunCountTotal)} />
          <StatCard label="Agent Runs (Avg)" value={formatInteger(metrics.summary.agentRunCountAvg)} />
          <StatCard label="Handoffs (Total)" value={formatInteger(metrics.summary.handoffCountTotal)} />
          <StatCard label="Handoffs (Avg)" value={formatInteger(metrics.summary.handoffCountAvg)} />
          <StatCard label="Gates (Total)" value={formatInteger(metrics.summary.gateEvaluationCountTotal)} />
          <StatCard label="Gates (Avg)" value={formatInteger(metrics.summary.gateEvaluationCountAvg)} />
          <StatCard label="Tool Errors (Avg)" value={formatInteger(metrics.summary.toolErrorCountAvg)} />
          <StatCard label="Reliability Issues (Avg)" value={formatInteger(metrics.summary.reliabilityIssueCountAvg)} />
          <StatCard label="Reliability Errors (Avg)" value={formatInteger(metrics.summary.reliabilityErrorCountAvg)} />
          <StatCard label="Finalization Failures (Avg)" value={formatInteger(metrics.summary.finalizationFailureCountAvg)} />
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-semibold text-slate-900">Per-Case Metrics</p>
          <p className="text-xs text-slate-500">{metrics.cases.length} rows</p>
        </div>
        <div className="mt-3 overflow-auto rounded-2xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Case Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">MAS Run ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">MAS Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Tokens</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Cost</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">LLM Calls</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Tool Calls</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Agent Runs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {metrics.cases.map((item) => (
                <tr key={item.testCaseId} className="hover:bg-slate-50/70">
                  <td className="px-4 py-3 text-sm font-medium text-slate-900">{item.testCaseName}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{item.swarmRunId ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{item.swarmStatus ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{formatLatencyMs(item.durationMs)}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{formatInteger(item.tokensTotal)}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{formatUsd(item.costUsdTotal)}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{formatInteger(item.llmCallCountTotal)}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{formatInteger(item.toolCallCountTotal)}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{formatInteger(item.agentRunCount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
          Raw Metrics JSON
        </summary>
        <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <JsonInspector value={metrics} />
        </div>
      </details>
    </div>
  );
}
