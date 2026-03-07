import { useId, useState } from 'react';
import type { AgentCatalogDetail } from '../../types/agents';
import { agentRunService } from '../../services/agentRunService';
import { AgentInputForm } from './AgentInputForm';
import { AgentTracesComponent } from './AgentTracesComponent';
import { SegmentedTabs } from '../ui/SegmentedTabs';

type OutputTabKey = 'traces' | 'results';

const outputTabs: Array<{ key: OutputTabKey; label: string }> = [
  { key: 'traces', label: 'Agent Traces' },
  { key: 'results', label: 'Results' },
];

type RunAgentTabProps = {
  agent: AgentCatalogDetail;
};

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
  const [view, setView] = useState<'input' | 'output'>('input');
  const [activeOutputTab, setActiveOutputTab] = useState<OutputTabKey>('traces');
  const [value, setValue] = useState<Record<string, unknown>>({});
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  async function handleRun() {
    setStartError(null);
    setStarting(true);

    try {
      const input = coerceInputForRun(agent.inputSchema, value);
      console.log('Starting agent run:', { agent_name: agent.name, input });

      const started = await agentRunService.startAgentRun(agent.name, input);
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
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 pt-2 h-full">
      <div>
        {view === 'input' && <p className="mt-1 text-md text-slate-600">
          Select tools and provide inputs to run this agent.
        </p>}
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
        <div className="mt-2 ">
          <SegmentedTabs
            idBase={outputTabsId}
            tabs={outputTabs}
            value={activeOutputTab}
            onChange={setActiveOutputTab}
            ariaLabel="Run output views"
          />

          <div className="mt-3 text-xs font-semibold text-slate-500">
            Run ID: <span className="font-mono text-slate-700">{runId ?? '—'}</span>
            {runStatus ? <span className="ml-2 text-slate-500">({runStatus})</span> : null}
          </div>

          <div className="mt-4 h-full">
            <div
              id={`${outputTabsId}-panel-traces`}
              role="tabpanel"
              aria-labelledby={`${outputTabsId}-tab-traces`}
              hidden={activeOutputTab !== 'traces'}
              className="h-full"
            >
              {runId ? <AgentTracesComponent key={runId} runId={runId} /> : null}
            </div>

            <div
              id={`${outputTabsId}-panel-results`}
              role="tabpanel"
              aria-labelledby={`${outputTabsId}-tab-results`}
              hidden={activeOutputTab !== 'results'}
              className="h-full"
            >
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <h4 className="text-sm font-semibold text-slate-900">Results</h4>
                <p className="mt-1 text-sm text-slate-600">
                  Results will appear here once the run endpoint is connected.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
