import { useId, useMemo, useState } from 'react';
import type { AgentCatalogDetail } from '../../../types/agents';
import type { AgentRunMetrics } from '../../../types/agentRuns';
import { agentRunService } from '../../../services/agentRunService';
import { AgentInputForm } from './AgentInputForm';
import { AgentTracesComponent } from './AgentTracesComponent';
import { SegmentedTabs } from '../../../shared/ui/SegmentedTabs';
import { Badge } from '../../../shared/ui/Badge';
import { useModels } from '../hooks/useModels';
import { RunStatusBadge } from './RunStatusBadge';
import { coerceInputForRun, getDefaultInputs } from '../utils/runInput';
import {
  buildEsi345ResultViewModel,
  buildResultViewModel,
  getAdditionalOutputEntries,
  getAgentDecisionConfig,
  isEsi345AgentName,
} from '../utils/runResult';
import { formatCurrency, formatDuration, formatInteger } from '../utils/format';
import { getReliabilitySummaryView } from '../utils/reliability';
import { AgentStatCard } from './shared/AgentStatCard';
import { AgentModelSelect } from './shared/AgentModelSelect';
import {
  AgentDecisionSummaryCards,
  AgentNarrativeSections,
} from './shared/AgentDecisionSummaryCards';
import { AgentAdditionalOutputFields } from './shared/AgentAdditionalOutputFields';
import { AgentRawJsonDetails } from './shared/AgentRawJsonDetails';
import { AgentReliabilitySummaryPanel } from './shared/AgentReliabilitySummaryPanel';

type OutputTabKey = 'traces' | 'results';

const outputTabs: Array<{ key: OutputTabKey; label: string }> = [
  { key: 'traces', label: 'Agent Traces' },
  { key: 'results', label: 'Results' },
];

type RunAgentTabProps = {
  agent: AgentCatalogDetail;
};

export default function RunAgentTab({ agent }: RunAgentTabProps) {
  const outputTabsId = useId();
  const modelSelectId = useId();
  const [view, setView] = useState<'input' | 'output'>('input');
  const [activeOutputTab, setActiveOutputTab] = useState<OutputTabKey>('traces');
  const [value, setValue] = useState<Record<string, unknown>>(() => getDefaultInputs(agent));
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [runOutput, setRunOutput] = useState<Record<string, unknown> | null>(null);
  const [runMetrics, setRunMetrics] = useState<AgentRunMetrics | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const { models, status: modelsStatus, selectedModelId, setSelectedModelId } = useModels();

  const decisionConfig = useMemo(() => getAgentDecisionConfig(agent.name), [agent.name]);
  const isEsi345Agent = useMemo(() => isEsi345AgentName(agent.name), [agent.name]);

  const resultView = useMemo(() => {
    if (!runOutput || isEsi345Agent) return null;
    return buildResultViewModel(runOutput, decisionConfig);
  }, [decisionConfig, isEsi345Agent, runOutput]);

  const esi345ResultView = useMemo(() => {
    if (!runOutput || !isEsi345Agent) return null;
    return buildEsi345ResultViewModel(runOutput);
  }, [isEsi345Agent, runOutput]);

  const additionalResultEntries = useMemo(() => {
    if (!runOutput) return [];
    return getAdditionalOutputEntries(runOutput, {
      decisionConfig,
      includeEsi345Aliases: isEsi345Agent,
    });
  }, [decisionConfig, isEsi345Agent, runOutput]);

  const reliabilitySummaryView = useMemo(
    () => getReliabilitySummaryView(runMetrics?.reliabilitySummary ?? null),
    [runMetrics?.reliabilitySummary],
  );

  async function refreshRunResults(targetRunId: string) {
    let done = false;
    const loadingTimer = window.setTimeout(() => {
      if (!done) setResultsLoading(true);
    }, 200);

    try {
      const run = await agentRunService.getAgentRun(targetRunId);
      if (run.outputJson) {
        const metrics = await agentRunService.getAgentRunMetrics(targetRunId);
        setRunMetrics(metrics);
      } else {
        setRunMetrics(null);
      }
      setRunStatus(run.status);
      setRunOutput(run.outputJson ?? null);
      setRunError(run.errorText ?? null);
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : 'Failed to load run results');
    } finally {
      done = true;
      window.clearTimeout(loadingTimer);
      setResultsLoading(false);
    }
  }

  async function handleRun() {
    setStartError(null);
    setStarting(true);
    setRunOutput(null);
    setRunError(null);
    setRunMetrics(null);

    try {
      const input = coerceInputForRun(agent.inputSchema, value);
      const started = await agentRunService.startAgentRun(
        agent.name,
        input,
        selectedModelId || undefined,
      );
      setRunId(started.runId);
      setRunStatus(started.status);
      setView('output');
      setActiveOutputTab('traces');
    } catch (e: unknown) {
      setStartError(e instanceof Error ? e.message : 'Failed to start agent run');
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-4 pt-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {view === 'input' ? (
          <>
            <p className="mt-1 text-md text-slate-600">Select tools and provide inputs to run this agent.</p>
            <div className="mt-1 flex items-center gap-2">
              <AgentModelSelect
                id={modelSelectId}
                models={models}
                modelsStatus={modelsStatus}
                selectedModelId={selectedModelId}
                setSelectedModelId={setSelectedModelId}
              />
            </div>
          </>
        ) : null}
      </div>

      {view === 'input' ? (
        <>
          <div className="mt-4">
            <AgentInputForm schema={agent.inputSchema} value={value} onChange={setValue} />
          </div>

          {startError ? (
            <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              {startError}
            </div>
          ) : null}

          <div className="mt-6 flex items-center justify-end">
            <button
              type="button"
              onClick={handleRun}
              disabled={starting}
              className="inline-flex items-center justify-center rounded-xl bg-PrimaryBlue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-PrimaryBlue/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
            >
              {starting ? 'Starting…' : 'Run Agent'}
            </button>
          </div>
        </>
      ) : (
        <div className="mt-2 flex min-h-0 flex-1 flex-col">
          <div className="flex items-center justify-between gap-3">
            <SegmentedTabs
              idBase={outputTabsId}
              tabs={outputTabs}
              value={activeOutputTab}
              onChange={setActiveOutputTab}
              ariaLabel="Run output views"
              className="w-[80%]"
            />
            <button
              type="button"
              onClick={() => setView('input')}
              className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
            >
              Back to inputs
            </button>
          </div>

          <div className="mt-3 text-xs font-semibold text-slate-500">
            Run ID: <span className="font-mono text-slate-700">{runId ?? '—'}</span>
            {runStatus ? <RunStatusBadge status={runStatus} className="ml-2" /> : null}
          </div>

          <div className="mt-4 min-h-0 flex-1">
            <div
              id={`${outputTabsId}-panel-traces`}
              role="tabpanel"
              aria-labelledby={`${outputTabsId}-tab-traces`}
              hidden={activeOutputTab !== 'traces'}
              className="h-full min-h-0 overflow-hidden"
            >
              {runId ? (
                <AgentTracesComponent
                  key={runId}
                  runId={runId}
                  onDone={(doneRunId) => {
                    if (doneRunId !== runId) return;
                    void refreshRunResults(doneRunId);
                  }}
                />
              ) : null}
            </div>

            <div
              id={`${outputTabsId}-panel-results`}
              role="tabpanel"
              aria-labelledby={`${outputTabsId}-tab-results`}
              hidden={activeOutputTab !== 'results'}
              className="h-full min-h-0 overflow-auto"
            >
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
                          <AgentStatCard
                            label="Total Tokens"
                            value={formatInteger(runMetrics?.tokens_total ?? null)}
                          />
                          <AgentStatCard
                            label="Duration"
                            value={formatDuration(runMetrics?.duration_seconds ?? null)}
                          />
                          <AgentStatCard
                            label="Cost"
                            value={formatCurrency(runMetrics?.cost_usd_total ?? null)}
                          />
                          <AgentStatCard
                            label="Tool Errors"
                            value={formatInteger(runMetrics?.tool_error_count ?? null)}
                            tone={
                              (runMetrics?.tool_error_count ?? 0) > 0
                                ? 'danger'
                                : runMetrics
                                  ? 'positive'
                                  : 'default'
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
                                <Badge
                                  key={`predicted-resource-${index}`}
                                  className="bg-sky-50 text-sky-700 ring-sky-200"
                                >
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
                            <AgentStatCard
                              label="Total Tokens"
                              value={formatInteger(runMetrics?.tokens_total ?? null)}
                            />
                            <AgentStatCard
                              label="Duration"
                              value={formatDuration(runMetrics?.duration_seconds ?? null)}
                            />
                            <AgentStatCard
                              label="Cost"
                              value={formatCurrency(runMetrics?.cost_usd_total ?? null)}
                            />
                            <AgentStatCard
                              label="Tool Errors"
                              value={formatInteger(runMetrics?.tool_error_count ?? null)}
                              tone={
                                (runMetrics?.tool_error_count ?? 0) > 0
                                  ? 'danger'
                                  : runMetrics
                                    ? 'positive'
                                    : 'default'
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

              {runMetrics ? (
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
                    <AgentStatCard
                      label="LLM Calls"
                      value={formatInteger(runMetrics.llm_call_count ?? null)}
                      tone="accent"
                    />
                    <AgentStatCard
                      label="Tool Calls"
                      value={formatInteger(runMetrics.tool_call_count ?? null)}
                    />
                    <AgentStatCard
                      label="Input Tokens"
                      value={formatInteger(runMetrics.input_tokens_total ?? null)}
                    />
                    <AgentStatCard
                      label="Output Tokens"
                      value={formatInteger(runMetrics.output_tokens_total ?? null)}
                    />
                    <AgentStatCard
                      label="Total Tokens"
                      value={formatInteger(runMetrics.tokens_total ?? null)}
                    />
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
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
