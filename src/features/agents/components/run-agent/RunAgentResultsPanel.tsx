import { Badge } from '../../../../shared/ui/Badge';
import type { AgentRunMetrics } from '../../../../types/agentRuns';
import type { Esi345ResultViewModel, ResultViewModel } from '../../utils/runResult';
import { formatCurrency, formatDuration, formatInteger } from '../../utils/format';
import { AgentAdditionalOutputFields } from '../shared/AgentAdditionalOutputFields';
import { AgentDecisionSummaryCards } from '../shared/AgentDecisionSummaryCards';
import { AgentNarrativeSections } from '../shared/AgentNarrativeSections';
import { AgentRawJsonDetails } from '../shared/AgentRawJsonDetails';
import { AgentStatCard } from '../shared/AgentStatCard';

type RunAgentResultsPanelProps = {
  runStatus: string | null;
  runError: string | null;
  runOutput: Record<string, unknown> | null;
  runMetrics: AgentRunMetrics | null;
  resultsLoading: boolean;
  isEsi345Agent: boolean;
  resultView: ResultViewModel | null;
  esi345ResultView: Esi345ResultViewModel | null;
  additionalResultEntries: Array<[string, unknown]>;
};

// Renders the run agent results panel.
export function RunAgentResultsPanel({
  runStatus,
  runError,
  runOutput,
  runMetrics,
  resultsLoading,
  isEsi345Agent,
  resultView,
  esi345ResultView,
  additionalResultEntries,
}: RunAgentResultsPanelProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-900">Results</h4>
        {resultsLoading ? (
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
            Loading…
          </span>
        ) : null}
        <Badge className="bg-white text-slate-700 ring-slate-200">
          {runStatus ? `Status: ${runStatus}` : 'Status unavailable'}
        </Badge>
      </div>

      {runError ? (
        <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {runError}
        </div>
      ) : runOutput && (isEsi345Agent ? esi345ResultView : resultView) ? (
        <div className="mt-3 space-y-4">
          {isEsi345Agent && esi345ResultView ? (
            <section className="rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,rgba(14,165,233,0.06)_0%,rgba(255,255,255,0.95)_42%,rgba(16,185,129,0.06)_100%)] p-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <AgentStatCard label="ESI Level" value={esi345ResultView.esiLevelLabel} tone="accent" />
                <AgentStatCard label="Num Resources" value={esi345ResultView.numResourcesLabel} />
                <AgentStatCard label="Total Tokens" value={formatInteger(runMetrics?.tokens_total ?? null)} />
                <AgentStatCard label="Duration" value={formatDuration(runMetrics?.duration_seconds ?? null)} />
                <AgentStatCard label="Cost" value={formatCurrency(runMetrics?.cost_usd_total ?? null)} />
                <AgentStatCard
                  label="Tool Errors"
                  value={formatInteger(runMetrics?.tool_error_count ?? null)}
                  tone={
                    (runMetrics?.tool_error_count ?? 0) > 0 ? 'danger' : runMetrics ? 'positive' : 'default'
                  }
                />
              </div>

              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Predicted Resources
                </h5>
                {esi345ResultView.predictedResources.length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {esi345ResultView.predictedResources.map((resource, index) => (
                      <Badge key={`predicted-resource-${index}`} className="bg-sky-50 text-sky-700 ring-sky-200">
                        {resource}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">No predicted resources were returned.</p>
                )}
              </div>
            </section>
          ) : resultView ? (
            <>
              <section className="rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,rgba(14,165,233,0.06)_0%,rgba(255,255,255,0.95)_42%,rgba(16,185,129,0.06)_100%)] p-4">
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  <AgentDecisionSummaryCards
                    decisionLabel={resultView.decisionLabel}
                    decisionTone={resultView.decisionTone}
                    confidenceLabel={resultView.confidenceLabel}
                  />
                  <AgentStatCard label="Total Tokens" value={formatInteger(runMetrics?.tokens_total ?? null)} />
                  <AgentStatCard label="Duration" value={formatDuration(runMetrics?.duration_seconds ?? null)} />
                  <AgentStatCard label="Cost" value={formatCurrency(runMetrics?.cost_usd_total ?? null)} />
                  <AgentStatCard
                    label="Tool Errors"
                    value={formatInteger(runMetrics?.tool_error_count ?? null)}
                    tone={
                      (runMetrics?.tool_error_count ?? 0) > 0 ? 'danger' : runMetrics ? 'positive' : 'default'
                    }
                  />
                </div>
              </section>

              <AgentNarrativeSections
                caseSummary={resultView.caseSummary}
                justification={resultView.justification}
                risks={resultView.risks}
                missingInformation={resultView.missingInformation}
              />
            </>
          ) : null}

          <AgentAdditionalOutputFields entries={additionalResultEntries} />
          <AgentRawJsonDetails summary="Raw Output JSON" value={runOutput} />
        </div>
      ) : runStatus && runStatus.toLowerCase().includes('run') ? (
        <p className="mt-2 text-sm text-slate-600">Waiting for the run to finish…</p>
      ) : (
        <p className="mt-2 text-sm text-slate-600">No output yet.</p>
      )}
    </div>
  );
}
