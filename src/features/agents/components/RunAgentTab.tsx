import { useId, useMemo, useState } from 'react';
import type { AgentCatalogDetail } from '../../../types/agents';
import { agentRunService } from '../../../services/agentRunService';
import { AgentInputForm } from './AgentInputForm';
import { AgentTracesComponent } from './AgentTracesComponent';
import { SegmentedTabs } from '../../../shared/ui/SegmentedTabs';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { Badge } from '../../../shared/ui/Badge';
import { cn } from '../../../shared/lib/cn';
import { useModels } from '../hooks/useModels';
import { RunStatusBadge } from './RunStatusBadge';
import { coerceInputForRun, getDefaultInputs } from '../utils/runInput';
import type { AgentRunMetrics } from '../../../types/agentRuns';

type OutputTabKey = 'traces' | 'results';

const outputTabs: Array<{ key: OutputTabKey; label: string }> = [
  { key: 'traces', label: 'Agent Traces' },
  { key: 'results', label: 'Results' },
];

type RunAgentTabProps = {
  agent: AgentCatalogDetail;
};

type ResultViewModel = {
  decisionLabel: string;
  decisionTone: 'positive' | 'danger' | 'neutral';
  confidenceLabel: string;
  caseSummary: string;
  justification: string;
  risks: string[];
  missingInformation: string[];
};

type StatCardProps = {
  label: string;
  value: string;
  tone?: 'default' | 'accent' | 'positive' | 'danger';
};

type AgentDecisionConfig = {
  decisionAliases: string[];
  trueLabel: string;
  falseLabel: string;
  trueKeywords: string[];
  falseKeywords: string[];
};

const RESULT_ALIASES = {
  confidence: ['confidence', 'score', 'probability'],
  summary: ['case_summary', 'casesummary', 'summary'],
  risks: ['key_risks', 'keyrisks', 'risks'],
  missing: ['missing_information', 'missinginformation', 'missing_info', 'gaps'],
  justification: ['justification', 'rationale', 'reasoning'],
} as const;

const DEFAULT_DECISION_CONFIG: AgentDecisionConfig = {
  decisionAliases: ['decision', 'ok', 'final_decision', 'finaldecision'],
  trueLabel: 'Positive',
  falseLabel: 'Negative',
  trueKeywords: [],
  falseKeywords: [],
};

const ESI1_DECISION_CONFIG: AgentDecisionConfig = {
  decisionAliases: ['is_esi1', 'isesi1', 'ok', 'decision', 'final_decision', 'finaldecision'],
  trueLabel: 'ESI-1',
  falseLabel: 'Not ESI-1',
  trueKeywords: ['esi1', 'esi-1'],
  falseKeywords: ['esi2', 'esi-2', 'esi3', 'esi-3', 'esi4', 'esi-4', 'esi5', 'esi-5'],
};

const ESI2_DECISION_CONFIG: AgentDecisionConfig = {
  decisionAliases: ['is_esi2', 'isesi2', 'ok', 'decision', 'final_decision', 'finaldecision'],
  trueLabel: 'ESI-2',
  falseLabel: 'Not ESI-2',
  trueKeywords: ['esi2', 'esi-2'],
  falseKeywords: ['esi1', 'esi-1', 'esi3', 'esi-3', 'esi4', 'esi-4', 'esi5', 'esi-5'],
};

function normalizeKey(key: string) {
  return key.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function getValueByAliases(record: Record<string, unknown>, aliases: readonly string[]) {
  const aliasSet = new Set(aliases.map(normalizeKey));
  for (const [key, value] of Object.entries(record)) {
    if (aliasSet.has(normalizeKey(key))) return value;
  }
  return undefined;
}

function toStringArray(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter((item) => item.trim().length > 0);
  }
  if (typeof value === 'string' && value.trim().length > 0) return [value];
  return [];
}

function titleCaseKey(key: string) {
  return key
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function asNumber(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function parseDecision(value: unknown) {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value > 0;
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (['true', 'yes', '1', 'retain', 'critical'].includes(normalized)) {
      return true;
    }
    if (['false', 'no', '0', 'defer'].includes(normalized)) {
      return false;
    }
  }
  return null;
}

function parseDecisionWithConfig(value: unknown, config: AgentDecisionConfig) {
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (config.trueKeywords.includes(normalized)) return true;
    if (config.falseKeywords.includes(normalized)) return false;
  }
  return parseDecision(value);
}

function getAgentDecisionConfig(agentName: string): AgentDecisionConfig {
  const normalized = normalizeKey(agentName);
  if (normalized.includes('esi2')) return ESI2_DECISION_CONFIG;
  if (normalized.includes('esi1')) return ESI1_DECISION_CONFIG;
  return DEFAULT_DECISION_CONFIG;
}

function formatInteger(value: number | null) {
  if (value == null) return '—';
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}

function formatDuration(seconds: number | null) {
  if (seconds == null) return '—';
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  return `${seconds.toFixed(seconds < 10 ? 2 : 1)} s`;
}

function formatCurrency(value: number | null) {
  if (value == null) return '—';
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 4,
  }).format(value);
}

function formatConfidence(value: number | null) {
  if (value == null) return '—';
  const ratio = value > 1 ? value / 100 : value;
  return `${Math.round(Math.max(0, Math.min(1, ratio)) * 100)}%`;
}

function statToneForDecision(tone: ResultViewModel['decisionTone']): StatCardProps['tone'] {
  if (tone === 'positive') return 'positive';
  if (tone === 'danger') return 'danger';
  return 'default';
}

function StatCard({ label, value, tone = 'default' }: StatCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-3',
        tone === 'positive' && 'border-emerald-200 bg-emerald-50/70',
        tone === 'danger' && 'border-rose-200 bg-rose-50/70',
        tone === 'accent' && 'border-sky-200 bg-sky-50/70',
        tone === 'default' && 'border-slate-200 bg-white',
      )}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-base font-semibold text-slate-900">{value}</p>
    </div>
  );
}

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

  const resultView = useMemo<ResultViewModel | null>(() => {
    if (!runOutput) return null;

    const decisionRaw = getValueByAliases(runOutput, decisionConfig.decisionAliases);
    const confidenceRaw = getValueByAliases(runOutput, RESULT_ALIASES.confidence);
    const summaryRaw = getValueByAliases(runOutput, RESULT_ALIASES.summary);
    const risksRaw = getValueByAliases(runOutput, RESULT_ALIASES.risks);
    const missingRaw = getValueByAliases(runOutput, RESULT_ALIASES.missing);
    const justificationRaw = getValueByAliases(runOutput, RESULT_ALIASES.justification);

    const decisionBool = parseDecisionWithConfig(decisionRaw, decisionConfig);
    const decisionLabel =
      decisionBool == null
        ? (typeof decisionRaw === 'string' ? decisionRaw : 'Unknown')
        : decisionBool
          ? decisionConfig.trueLabel
          : decisionConfig.falseLabel;
    const decisionTone: ResultViewModel['decisionTone'] =
      decisionBool == null ? 'neutral' : decisionBool ? 'positive' : 'danger';

    const confidence = asNumber(confidenceRaw);
    const caseSummary =
      typeof summaryRaw === 'string' && summaryRaw.trim().length > 0
        ? summaryRaw
        : 'No summary was provided by the run output.';
    const justification =
      typeof justificationRaw === 'string' && justificationRaw.trim().length > 0
        ? justificationRaw
        : 'No justification was provided by the run output.';

    return {
      decisionLabel,
      decisionTone,
      confidenceLabel: formatConfidence(confidence),
      caseSummary,
      justification,
      risks: toStringArray(risksRaw),
      missingInformation: toStringArray(missingRaw),
    };
  }, [runOutput, decisionConfig]);

  const additionalResultEntries = useMemo(() => {
    if (!runOutput) return [];
    const knownKeys = new Set(
      [
        ...decisionConfig.decisionAliases,
        ...RESULT_ALIASES.confidence,
        ...RESULT_ALIASES.summary,
        ...RESULT_ALIASES.risks,
        ...RESULT_ALIASES.missing,
        ...RESULT_ALIASES.justification,
      ].map(normalizeKey),
    );
    return Object.entries(runOutput).filter(([key]) => !knownKeys.has(normalizeKey(key)));
  }, [runOutput, decisionConfig]);

  const reliabilitySummary = runMetrics?.reliabilitySummary ?? null;
  const reliabilityByCode = reliabilitySummary?.byCode ?? [];
  const reliabilityTotalIssues = reliabilitySummary?.totalIssues ?? null;
  const reliabilityErrorIssues = reliabilitySummary?.errorIssues ?? null;
  const reliabilityHasIssues = (reliabilitySummary?.totalIssues ?? 0) > 0;
  const reliabilityHasErrors = (reliabilitySummary?.errorIssues ?? 0) > 0;

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
              <label htmlFor={modelSelectId} className="text-xs font-semibold text-slate-700">
                Model
              </label>
              <select
                id={modelSelectId}
                value={selectedModelId}
                onChange={(e) => setSelectedModelId(e.target.value)}
                disabled={modelsStatus !== 'success' || models.length === 0}
                className="min-w-48 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
              >
                {modelsStatus === 'loading' ? <option value="">Loading…</option> : null}
                {modelsStatus === 'error' ? <option value="">Unavailable</option> : null}
                {modelsStatus === 'success'
                  ? models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.id} ({model.provider})
                    </option>
                  ))
                  : null}
              </select>
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

          <div className="mt-4 flex-1 min-h-0">
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
                    refreshRunResults(doneRunId);
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
                ) : runOutput && resultView ? (
                  <div className="mt-3 space-y-4">
                    <section className="rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,rgba(14,165,233,0.06)_0%,rgba(255,255,255,0.95)_42%,rgba(16,185,129,0.06)_100%)] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">


                      </div>
                      <div className=" grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        <StatCard
                          label="Decision"
                          value={resultView.decisionLabel}
                          tone={statToneForDecision(resultView.decisionTone)}
                        />
                        <StatCard label="Confidence" value={resultView.confidenceLabel} tone="accent" />
                        <StatCard
                          label="Total Tokens"
                          value={formatInteger(runMetrics?.tokens_total ?? null)}
                        />
                        <StatCard
                          label="Duration"
                          value={formatDuration(runMetrics?.duration_seconds ?? null)}
                        />
                        <StatCard label="Cost" value={formatCurrency(runMetrics?.cost_usd_total ?? null)} />
                        <StatCard
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

                    <section className="grid gap-4 xl:grid-cols-2">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Clinical Summary
                        </h5>
                        <p className="mt-2 text-sm leading-relaxed text-slate-800">
                          {resultView.caseSummary}
                        </p>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Justification
                        </h5>
                        <p className="mt-2 text-sm leading-relaxed text-slate-800">
                          {resultView.justification}
                        </p>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Key Risks
                        </h5>
                        {resultView.risks.length ? (
                          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-800">
                            {resultView.risks.map((risk, index) => (
                              <li key={`risk-${index}`}>{risk}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="mt-2 text-sm text-slate-500">No key risks were returned.</p>
                        )}
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Missing Information
                        </h5>
                        {resultView.missingInformation.length ? (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {resultView.missingInformation.map((item, index) => (
                              <Badge
                                key={`missing-${index}`}
                                className="bg-amber-50 text-amber-700 ring-amber-200"
                              >
                                {item}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <div className="mt-2">
                            <Badge className="bg-emerald-50 text-emerald-700 ring-emerald-200">
                              None detected
                            </Badge>
                          </div>
                        )}
                      </div>
                    </section>

                    {additionalResultEntries.length ? (
                      <details className="rounded-2xl border border-slate-200 bg-white p-4">
                        <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
                          Additional Output Fields
                        </summary>
                        <div className="mt-3 grid gap-3 md:grid-cols-2">
                          {additionalResultEntries.map(([key, item]) => (
                            <div key={key} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                {titleCaseKey(key)}
                              </p>
                              <div className="mt-2 max-h-40 overflow-auto text-sm text-slate-800">
                                {item != null && typeof item === 'object' ? (
                                  <JsonInspector value={item} />
                                ) : (
                                  <p>{String(item ?? '—')}</p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </details>
                    ) : null}

                    <details className="rounded-2xl border border-slate-200 bg-white p-4">
                      <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
                        Raw Output JSON
                      </summary>
                      <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                        <JsonInspector value={runOutput} />
                      </div>
                    </details>
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
                    <StatCard
                      label="LLM Calls"
                      value={formatInteger(runMetrics.llm_call_count ?? null)}
                      tone="accent"
                    />
                    <StatCard
                      label="Tool Calls"
                      value={formatInteger(runMetrics.tool_call_count ?? null)}
                    />
                    <StatCard
                      label="Input Tokens"
                      value={formatInteger(runMetrics.input_tokens_total ?? null)}
                    />
                    <StatCard
                      label="Output Tokens"
                      value={formatInteger(runMetrics.output_tokens_total ?? null)}
                    />
                    <StatCard
                      label="Total Tokens"
                      value={formatInteger(runMetrics.tokens_total ?? null)}
                    />
                    <StatCard
                      label="Failure Reason"
                      value={runMetrics.failure_reason || 'None'}
                      tone={runMetrics.failure_reason ? 'danger' : 'positive'}
                    />
                  </div>

                  <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Reliability Summary
                    </p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <StatCard
                        label="Total Issues"
                        value={formatInteger(reliabilityTotalIssues)}
                        tone={
                          reliabilitySummary == null
                            ? 'default'
                            : reliabilityHasIssues
                              ? 'danger'
                              : 'positive'
                        }
                      />
                      <StatCard
                        label="Error Issues"
                        value={formatInteger(reliabilityErrorIssues)}
                        tone={
                          reliabilitySummary == null
                            ? 'default'
                            : reliabilityHasErrors
                              ? 'danger'
                              : 'positive'
                        }
                      />
                      <StatCard
                        label="Issue Codes"
                        value={formatInteger(reliabilityByCode.length)}
                        tone={reliabilityByCode.length ? 'accent' : 'default'}
                      />
                      <StatCard
                        label="Reliability Status"
                        value={
                          reliabilitySummary == null
                            ? 'Unavailable'
                            : reliabilityHasIssues
                              ? 'Issues Detected'
                              : 'Healthy'
                        }
                        tone={
                          reliabilitySummary == null
                            ? 'default'
                            : reliabilityHasIssues
                              ? 'danger'
                              : 'positive'
                        }
                      />
                    </div>

                    {reliabilityByCode.length ? (
                      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {reliabilityByCode.map((item) => (
                          <StatCard
                            key={item.issueCode}
                            label={titleCaseKey(item.issueCode)}
                            value={formatInteger(item.count)}
                            tone={item.count > 0 ? 'danger' : 'default'}
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Raw Metrics JSON
                    </summary>
                    <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-white p-3">
                      <JsonInspector value={runMetrics} />
                    </div>
                  </details>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
