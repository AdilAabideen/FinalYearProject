import { JsonInspector } from '../../../../shared/ui/JsonInspector';
import { Badge } from '../../../../shared/ui/Badge';
import { AgentStatCard as StatCard, type AgentStatCardTone } from '../shared/AgentStatCard';
import { formatInteger, formatPercent } from '../../utils/format';
import { ConfusionCell } from './ConfusionCell';

type AgentTestRunResultsPanelProps = {
  error: string | null;
  runId: string | null;
  runPhase: 'idle' | 'running' | 'done';
  runMetrics: Record<string, unknown> | null;
  summaryTotal: number;
  summaryPassed: number;
  summaryFailed: number;
  summaryExecFailed: number;
  summaryInvalidPred: number;
  summaryPassRate: number | null;
  summaryPassRateLabel: string;
  summaryPassRateTone: AgentStatCardTone;
  agentName: string;
  classification: {
    label?: string;
    tp?: number;
    tn?: number;
    fp?: number;
    fn?: number;
    n_eval?: number;
    accuracy?: number;
    precision?: number | null;
    recall?: number | null;
    f1?: number | null;
    specificity?: number | null;
    excluded?: {
      exec_failed?: number;
      invalid_pred?: number;
      other?: number;
    };
  } | null;
  tp: number;
  tn: number;
  fp: number;
  fn: number;
  confusionMax: number;
};

// Renders the agent test run results.
export function AgentTestRunResultsPanel({
  error,
  runId,
  runPhase,
  runMetrics,
  summaryTotal,
  summaryPassed,
  summaryFailed,
  summaryExecFailed,
  summaryInvalidPred,
  summaryPassRate,
  summaryPassRateLabel,
  summaryPassRateTone,
  agentName,
  classification,
  tp,
  tn,
  fp,
  fn,
  confusionMax,
}: AgentTestRunResultsPanelProps) {
  if (error) {
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>;
  }

  if (!runId && runPhase === 'idle') {
    return <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">Test not run. Please start a test run.</div>;
  }

  if (runPhase === 'running') {
    return <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">Currently running test…</div>;
  }

  if (runPhase !== 'done') {
    return <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">Results not available yet.</div>;
  }

  return (
    <div className="space-y-4 pb-3">
      <section className="rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,rgba(14,165,233,0.08)_0%,rgba(255,255,255,0.98)_42%,rgba(16,185,129,0.08)_100%)] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Run Summary</p>
            <p className="text-sm text-slate-700">Final aggregate metrics for this test harness execution.</p>
          </div>
          <Badge
            className={
              summaryPassRate == null
                ? 'bg-white text-slate-700 ring-slate-200'
                : summaryPassRate >= 0.8
                  ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                  : summaryPassRate >= 0.6
                    ? 'bg-sky-50 text-sky-700 ring-sky-200'
                    : 'bg-rose-50 text-rose-700 ring-rose-200'
            }
          >
            Pass Rate: {summaryPassRateLabel}
          </Badge>
        </div>

        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-200">
          <div
            className={`h-full rounded-full transition-all ${
              summaryPassRate == null
                ? 'bg-slate-300'
                : summaryPassRate >= 0.8
                  ? 'bg-emerald-500'
                  : summaryPassRate >= 0.6
                    ? 'bg-sky-500'
                    : 'bg-rose-500'
            }`}
            style={{ width: summaryPassRate == null ? '0%' : `${Math.max(0, Math.min(summaryPassRate, 1)) * 100}%` }}
          />
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Total Cases" value={formatInteger(summaryTotal)} />
          <StatCard label="Passed" value={formatInteger(summaryPassed)} tone="positive" />
          <StatCard label="Failed" value={formatInteger(summaryFailed)} tone={summaryFailed > 0 ? 'danger' : 'default'} />
          <StatCard label="Pass Rate" value={summaryPassRateLabel} tone={summaryPassRateTone} />
          <StatCard label="Exec Failed" value={formatInteger(summaryExecFailed)} tone={summaryExecFailed > 0 ? 'danger' : 'default'} />
          <StatCard label="Invalid Pred" value={formatInteger(summaryInvalidPred)} tone={summaryInvalidPred > 0 ? 'danger' : 'default'} />
        </div>
      </section>

      {classification ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Classification ({classification.label ?? 'N/A'})
            </p>
            <Badge className="bg-white text-slate-700 ring-slate-200">
              Evaluated: {formatInteger(classification.n_eval ?? null)}
            </Badge>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard label="Accuracy" value={formatPercent(classification.accuracy ?? null, 2)} tone="accent" />
            <StatCard label="Precision" value={formatPercent(classification.precision ?? null, 2)} />
            <StatCard label="Recall" value={formatPercent(classification.recall ?? null, 2)} />
            <StatCard label="F1 Score" value={formatPercent(classification.f1 ?? null, 2)} />
            <StatCard label="Specificity" value={formatPercent(classification.specificity ?? null, 2)} />
            <StatCard label="Evaluated Cases" value={formatInteger(classification.n_eval ?? null)} />
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-[2fr_1fr]">
            {agentName !== 'single_agent' && (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Confusion Matrix</p>
                <div className="mt-2 grid grid-cols-[5.5rem_1fr_1fr] gap-2">
                  <div />
                  <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-600">Predicted Positive</div>
                  <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-600">Predicted Negative</div>
                  <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-600">Actual Positive</div>
                  <ConfusionCell label="TP" value={tp} tone="correct" maxValue={confusionMax} />
                  <ConfusionCell label="FN" value={fn} tone="error" maxValue={confusionMax} />
                  <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-600">Actual Negative</div>
                  <ConfusionCell label="FP" value={fp} tone="error" maxValue={confusionMax} />
                  <ConfusionCell label="TN" value={tn} tone="correct" maxValue={confusionMax} />
                </div>
              </div>
            )}

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 w-full">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Excluded</p>
              <div className="mt-3 space-y-2">
                <StatCard label="Exec Failed" value={formatInteger(classification.excluded?.exec_failed ?? null)} tone={(classification.excluded?.exec_failed ?? 0) > 0 ? 'danger' : 'default'} />
                <StatCard label="Invalid Pred" value={formatInteger(classification.excluded?.invalid_pred ?? null)} tone={(classification.excluded?.invalid_pred ?? 0) > 0 ? 'danger' : 'default'} />
                <StatCard label="Other" value={formatInteger(classification.excluded?.other ?? null)} tone={(classification.excluded?.other ?? 0) > 0 ? 'danger' : 'default'} />
              </div>
            </div>
          </div>
        </section>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
          Classification metrics were not returned for this run.
        </div>
      )}

      {runMetrics ? (
        <details className="rounded-2xl border border-slate-200 bg-white p-4">
          <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">Raw Run Metrics JSON</summary>
          <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <JsonInspector value={runMetrics} />
          </div>
        </details>
      ) : null}
    </div>
  );
}
