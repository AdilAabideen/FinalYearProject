import type { SwarmRunMetricsRead } from '../../../types/masRuns';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { AgentStatCard as StatCard } from '../../agents/components/shared/AgentStatCard';
import {
  formatCurrency,
  formatInteger,
  formatLatencyMs,
  titleCaseKey,
} from '../../agents/utils/format';

type MasMetricsTabProps = {
  metrics: SwarmRunMetricsRead | null;
};

// Renders the MAS metrics tab.
export default function MasMetricsTab({ metrics }: MasMetricsTabProps) {
  const failureReasonEntries: Array<[string, number]> = metrics
    ? ([
      ['agent failures', metrics.agentFailureCount],
      ['reliability issues', metrics.reliabilityIssueCount],
      ['reliability errors', metrics.reliabilityErrorCount],
      ['finalization failures', metrics.finalizationFailureCount],
    ] as Array<[string, number]>).filter(([, count]) => count > 0)
    : [];

  return (
    <div className="h-full min-h-0 overflow-auto">
      {!metrics ? (
        <div>
          <p className='text-xl font-semibold text-slate-900 mb-2 border-b border-slate-200 p-3 '>Mas Metrics</p>
          <div className="  bg-white p-3 px-4 text-md text-slate-800">
            Run metrics not available yet. Please Wait for a Test case to finish 
          </div>
        </div>
      ) : (
        <div className="pb-3">
          <section className="rounded  bg-white">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className='w-full border-b border-slate-200 p-3'>
                <p className='text-xl font-semibold text-slate-900 mb-[3px] '>Mas Metrics</p>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Aggregated Run Summary
                </p>
                <p className="mt-1 text-sm text-slate-700">
                  Summary-level metrics for this MAS run.
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 p-3 pb-0">
              <StatCard
                label="Cost Per Agent Run"
                value={formatCurrency(metrics.costUsdPerAgentRun ?? null)}
                tone="accent"
              />
              <StatCard
                label="Total Cost"
                value={formatCurrency(metrics.costUsdTotal ?? null)}
                tone="accent"
              />
              <StatCard
                label="Duration (ms)"
                value={formatLatencyMs(metrics.durationMs ?? null)}
              />
              <StatCard
                label="Failed Agent Runs"
                value={formatInteger(metrics.failedAgentCount)}
                tone={metrics.failedAgentCount > 0 ? 'danger' : 'default'}
              />
              <StatCard
                label="LLM Calls"
                value={formatInteger(metrics.llmCallCountTotal)}
              />
              <StatCard
                label="Tool Calls"
                value={formatInteger(metrics.toolCallCountTotal)}
              />
              <StatCard
                label="Tool Errors"
                value={formatInteger(metrics.toolErrorCountTotal)}
                tone={metrics.toolErrorCountTotal > 0 ? 'danger' : 'default'}
              />
              <StatCard
                label="Handoffs"
                value={formatInteger(metrics.handoffCount)}
              />
            </div>

            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 p-3 pt-0">
              <StatCard
                label="Input Tokens"
                value={formatInteger(metrics.inputTokensTotal)}
              />
              <StatCard
                label="Output Tokens"
                value={formatInteger(metrics.outputTokensTotal)}
              />
              <StatCard
                label="Total Tokens"
                value={formatInteger(metrics.tokensTotal)}
              />
              <StatCard
                label="Agent Runs"
                value={formatInteger(metrics.agentRunCount)}
              />
              <StatCard
                label="Completed Agents"
                value={formatInteger(metrics.completedAgentCount)}
                tone="positive"
              />
              <StatCard
                label="Gate Evaluations"
                value={formatInteger(metrics.gateEvaluationCount)}
              />
            </div>
          </section>

          <section className="rounded-non border border-l-0 border-slate-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Failure Reason Issues
            </p>
            {failureReasonEntries.length ? (
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {failureReasonEntries.map(([reason, count]) => (
                  <StatCard
                    key={reason}
                    label={titleCaseKey(reason)}
                    value={formatInteger(count)}
                    tone={count > 0 ? 'danger' : 'default'}
                  />
                ))}
              </div>
            ) : (
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <StatCard label="Failure Reason Issues" value="None detected" tone="positive" />
              </div>
            )}
          </section>

          <details className="rounded-none border-l-0 border border-slate-200 bg-white p-4">
            <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
              Raw Summary JSON
            </summary>
            <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <JsonInspector value={metrics} />
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
