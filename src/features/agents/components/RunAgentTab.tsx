import { useId, useState } from 'react';
import type { AgentCatalogDetail } from '../../../types/agents';
import { agentRunService } from '../../../services/agentRunService';
import { AgentInputForm } from './AgentInputForm';
import { AgentTracesComponent } from './AgentTracesComponent';
import { SegmentedTabs } from '../../../shared/ui/SegmentedTabs';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { useModels } from '../hooks/useModels';
import { RunStatusBadge } from './RunStatusBadge';

type OutputTabKey = 'traces' | 'results';

const outputTabs: Array<{ key: OutputTabKey; label: string }> = [
  { key: 'traces', label: 'Agent Traces' },
  { key: 'results', label: 'Results' },
];

type RunAgentTabProps = {
  agent: AgentCatalogDetail;
};

function getDefaultInputs(agent: AgentCatalogDetail): Record<string, unknown> {
  if (agent.name !== 'vitals_agent') return {};

  return {
    temperature: '98.3',
    heartrate: '75',
    resprate: '14',
    o2sat: '100',
    sbp: '138',
    dbp: '90',
    pain: '7',
    subject_id: '19880634',
    intime: '2199-10-08T16:40',
    age_years: '49.7',
    chiefcomplaint: 'Left Abdominal Pain',
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function getStringFormat(schema: unknown): string | undefined {
  if (!isRecord(schema)) return undefined;
  return typeof schema.format === 'string' && schema.format.trim().length ? schema.format : undefined;
}

function getTypeCandidates(schema: unknown): string[] {
  if (!isRecord(schema)) return [];
  const types: string[] = [];

  const directType = schema.type;
  if (typeof directType === 'string') types.push(directType);
  if (Array.isArray(directType)) {
    for (const t of directType) if (typeof t === 'string') types.push(t);
  }

  const unions = schema.anyOf ?? schema.oneOf;
  if (Array.isArray(unions)) {
    for (const option of unions) types.push(...getTypeCandidates(option));
  }

  return Array.from(new Set(types));
}

function getPrimaryType(schema: unknown): string | undefined {
  const types = getTypeCandidates(schema).filter((t) => t !== 'null');
  return types[0];
}

function coerceInputForRun(inputSchema: Record<string, unknown>, raw: Record<string, unknown>) {
  const properties = isRecord(inputSchema.properties) ? inputSchema.properties : {};
  const required = new Set(
    Array.isArray(inputSchema.required)
      ? inputSchema.required.filter((k): k is string => typeof k === 'string' && k.length > 0)
      : [],
  );

  const output: Record<string, unknown> = {};

  for (const [key, schema] of Object.entries(properties)) {
    const rawValue = raw[key];

    if (rawValue == null || rawValue === '') {
      if (required.has(key)) throw new Error(`Missing required field: ${key}`);
      continue;
    }

    const primaryType = getPrimaryType(schema);
    const stringFormat = getStringFormat(schema);

    if ((primaryType === 'number' || primaryType === 'integer') && typeof rawValue === 'string') {
      const num = Number(rawValue);
      if (!Number.isFinite(num)) throw new Error(`Invalid number for ${key}`);
      output[key] = primaryType === 'integer' ? Math.trunc(num) : num;
      continue;
    }

    if (primaryType === 'integer' && typeof rawValue === 'number') {
      output[key] = Math.trunc(rawValue);
      continue;
    }

    if (primaryType === 'number' && typeof rawValue === 'number') {
      output[key] = rawValue;
      continue;
    }

    if (primaryType === 'string' && stringFormat === 'date-time' && typeof rawValue === 'string') {
      output[key] = rawValue;
      continue;
    }

    output[key] = rawValue;
  }

  return output;
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
  const [runError, setRunError] = useState<string | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const { models, status: modelsStatus, selectedModelId, setSelectedModelId } = useModels();

  async function refreshRunResults(targetRunId: string) {
    let done = false;
    const loadingTimer = window.setTimeout(() => {
      if (!done) setResultsLoading(true);
    }, 200);

    try {
      const run = await agentRunService.getAgentRun(targetRunId);
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
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 pt-2 h-full flex min-h-0 flex-col">
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


          <div className="flex flex-row justify-between items-center">
            <SegmentedTabs
              idBase={outputTabsId}
              tabs={outputTabs}
              value={activeOutputTab}
              onChange={setActiveOutputTab}
              ariaLabel="Run output views"
              className="w-[80%]"
            />
            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setView('input')}
                className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs font-semibold text-slate-700  transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
              >
                Back to inputs
              </button>
            </div>

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
                </div>

                {runError ? (
                  <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                    {runError}
                  </div>
                ) : runOutput ? (
                  <div className="mt-3 max-h-[min(28rem,60vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <JsonInspector value={runOutput} />
                  </div>
                ) : runStatus && runStatus.toLowerCase().includes('run') ? (
                  <p className="mt-2 text-sm text-slate-600">Waiting for the run to finish…</p>
                ) : (
                  <p className="mt-2 text-sm text-slate-600">No output yet.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
