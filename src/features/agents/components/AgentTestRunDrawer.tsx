import { useCallback, useEffect, useId, useMemo, useState, type ReactElement } from 'react';
import type { AgentTestCaseRead } from '../../../types/agentTests';
import { API_BASE_URL } from '../../../config/env';
import { agentRunService } from '../../../services/agentRunService';
import { AgentTracesComponent } from './AgentTracesComponent';
import { SegmentedTabs } from '../../../shared/ui/SegmentedTabs';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { Badge } from '../../../shared/ui/Badge';
import { useModels } from '../hooks/useModels';

type HarnessTabKey = 'cases' | 'results';
type ViewerTabKey = 'case_details' | 'test_traces' | 'outputs' | 'diff' | 'metrics';
type CaseStatus = 'pending' | 'running' | 'passed' | 'failed';
type RunPhase = 'idle' | 'running' | 'done';

type RunMetrics = {
  total?: number;
  passed?: number;
  failed?: number;
  exec_failed?: number;
  invalid_pred?: number;
  pass_rate?: number;
  classification?: {
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
  };
};

type CaseOutputState = {
  status: 'idle' | 'loading' | 'ready' | 'error';
  agentRunId?: string;
  output?: Record<string, unknown> | null;
  error?: string;
};

type CaseMetricsState = {
  status: 'idle' | 'loading' | 'ready' | 'error';
  agentRunId?: string;
  metrics?: Record<string, unknown> | null;
  error?: string;
}

type CaseDiffState = {
  status: 'idle' | 'loading' | 'ready' | 'error';
  agentRunId?: string;
  diff?: Record<string, unknown> | null;
  error?: string;
}

type CaseResultViewModel = {
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

type DiffRenderer = (diff: Record<string, unknown>) => ReactElement;

const harnessTabs: Array<{ key: HarnessTabKey; label: string }> = [
  { key: 'cases', label: 'Test Cases' },
  { key: 'results', label: 'Test Results' },
];

const viewerTabs: Array<{ key: ViewerTabKey; label: string }> = [
  { key: 'case_details', label: 'Details' },
  { key: 'test_traces', label: 'Test Traces' },
  { key: 'outputs', label: 'Outputs' },
  { key: 'diff', label: 'Diff' },
  { key: 'metrics', label: 'Metrics' },
];

const friendlyLabels: Record<string, string> = {
  age_years: 'Age',
  chiefcomplaint: 'Chief Complaint',
  dbp: 'DBP',
  heartrate: 'Heart Rate',
  intime: 'Intime',
  o2sat: 'O₂ Sat',
  pain: 'Pain',
  resprate: 'Resp Rate',
  sbp: 'SBP',
  temperature: 'Temperature',
  subject_id: 'Subject ID',
};

const RESULT_ALIASES = {
  decision: ['is_esi1', 'isesi1', 'ok', 'decision', 'final_decision', 'finaldecision'],
  confidence: ['confidence', 'score', 'probability'],
  summary: ['case_summary', 'casesummary', 'summary'],
  risks: ['key_risks', 'keyrisks', 'risks'],
  missing: ['missing_information', 'missinginformation', 'missing_info', 'gaps'],
  justification: ['justification', 'rationale', 'reasoning'],
} as const;

type AgentTestRunDrawerProps = {
  agentName: string;
  runId: string | null;
  selectedCases: AgentTestCaseRead[];
  busy: boolean;
  error: string | null;
  onStart: (modelId?: string) => void | Promise<void>;
};

function CaseBadge({ label, value }: { label: string; value: string | number }) {
  const display = friendlyLabels[label] ?? label;
  return (
    <span className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-700">
      {display}: {value}
    </span>
  );
}

function StatusDot({ status }: { status: CaseStatus }) {
  const color =
    status === 'running'
      ? 'bg-orange-400'
      : status === 'passed'
        ? 'bg-emerald-500'
        : status === 'failed'
          ? 'bg-rose-500'
          : 'bg-slate-300';
  return <span className={`inline-flex h-2.5 w-2.5 rounded-full ${color}`} />;
}

function titleCase(value: string) {
  return value.replace(/\b\w/g, (c) => c.toUpperCase());
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

function extractCaseId(payload: Record<string, unknown>) {
  return (
    asString(payload.test_case_id) ??
    asString(payload.case_id) ??
    (isRecord(payload.result)
      ? asString(payload.result.test_case_id) ?? asString(payload.result.case_id)
      : undefined) ??
    (isRecord(payload.payload_json)
      ? asString(payload.payload_json.test_case_id) ?? asString(payload.payload_json.case_id)
      : undefined)
  );
}

function extractAgentRunId(payload: Record<string, unknown>) {
  return (
    asString(payload.agent_run_id) ??
    asString(payload.run_id) ??
    (isRecord(payload.result)
      ? asString(payload.result.agent_run_id) ?? asString(payload.result.run_id)
      : undefined) ??
    (isRecord(payload.payload_json)
      ? asString(payload.payload_json.agent_run_id) ?? asString(payload.payload_json.run_id)
      : undefined)
  );
}

function extractPassed(payload: Record<string, unknown>) {
  if (typeof payload.passed === 'boolean') return payload.passed;
  const status =
    asString(payload.status) ??
    (isRecord(payload.result) ? asString(payload.result.status) : undefined) ??
    (isRecord(payload.payload_json) ? asString(payload.payload_json.status) : undefined) ??
    '';
  return status.toLowerCase().includes('pass');
}

function extractMetrics(payload: Record<string, unknown>) {
  if (isRecord(payload.metrics)) return payload.metrics as RunMetrics;
  if (isRecord(payload.metrics_json)) return payload.metrics_json as RunMetrics;
  if (isRecord(payload.result) && isRecord(payload.result.metrics)) return payload.result.metrics as RunMetrics;
  return null;
}

function extractDiff(payload: Record<string, unknown>) {

  if (isRecord(payload.diff_json)) return payload.diff_json;
  if (isRecord(payload.result) && isRecord(payload.result.diff_json)) return payload.result.diff_json;
  if (isRecord(payload.payload_json) && isRecord(payload.payload_json.diff_json)) return payload.payload_json.diff_json;

  return null;
}

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
    if (['true', 'yes', '1', 'retain', 'esi1', 'esi-1', 'critical'].includes(normalized)) {
      return true;
    }
    if (['false', 'no', '0', 'defer', 'esi2', 'esi3', 'esi4', 'esi5'].includes(normalized)) {
      return false;
    }
  }
  return null;
}

function formatConfidence(value: number | null) {
  if (value == null) return '—';
  const ratio = value > 1 ? value / 100 : value;
  return `${Math.round(Math.max(0, Math.min(1, ratio)) * 100)}%`;
}

function titleCaseKey(key: string) {
  return key
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
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

function formatPercent(value: number | null, digits = 1) {
  if (value == null || !Number.isFinite(value)) return '—';
  const ratio = value > 1 ? value / 100 : value;
  const clamped = Math.max(0, Math.min(1, ratio));
  return `${(clamped * 100).toFixed(digits)}%`;
}

function StatCard({ label, value, tone = 'default' }: StatCardProps) {
  const toneClass =
    tone === 'positive'
      ? 'border-emerald-200 bg-emerald-50/70'
      : tone === 'danger'
        ? 'border-rose-200 bg-rose-50/70'
        : tone === 'accent'
          ? 'border-sky-200 bg-sky-50/70'
          : 'border-slate-200 bg-white';

  return (
    <div className={`rounded-xl border p-3 ${toneClass}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-base font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function ConfusionCell({
  label,
  value,
  tone,
  maxValue,
}: {
  label: string;
  value: number;
  tone: 'correct' | 'error';
  maxValue: number;
}) {
  const ratio = maxValue > 0 ? value / maxValue : 0;
  const strength = ratio > 0.66 ? 'strong' : ratio > 0.33 ? 'medium' : 'soft';
  const className =
    tone === 'correct'
      ? strength === 'strong'
        ? 'border-emerald-300 bg-emerald-100 text-emerald-900'
        : strength === 'medium'
          ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
          : 'border-emerald-100 bg-emerald-50/40 text-emerald-900'
      : strength === 'strong'
        ? 'border-rose-300 bg-rose-100 text-rose-900'
        : strength === 'medium'
          ? 'border-rose-200 bg-rose-50 text-rose-900'
          : 'border-rose-100 bg-rose-50/40 text-rose-900';

  return (
    <div className={`rounded-xl border p-3 ${className}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-xl font-semibold">{formatInteger(value)}</p>
    </div>
  );
}

function normalizeAgentName(name: string) {
  return name.trim().toLowerCase().replace(/[\s_-]+/g, '');
}

function renderGenericDiff(diff: Record<string, unknown>) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-sm font-semibold text-slate-900">Diff</p>
      <p className="mt-1 text-xs text-slate-600">No agent-specific renderer configured for this agent.</p>
      <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
        <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-slate-600">
          Raw Diff JSON
        </summary>
        <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-white p-3">
          <JsonInspector value={diff} />
        </div>
      </details>
    </div>
  );
}

function renderEsiDiff(diff: Record<string, unknown>) {
  const expectedAnswer = isRecord(diff.expected_answer) ? diff.expected_answer : {};
  const agentAnswer = isRecord(diff.agent_answer) ? diff.agent_answer : {};

  const expectedAcuity = asNumber(expectedAnswer.acuity);
  const isEsi1 = parseDecision(agentAnswer.is_esi1);
  const confidence = asNumber(agentAnswer.confidence);

  const isMatch = diff.passed

  const verdictLabel = isMatch == null ? 'Not enough data' : isMatch ? 'Success' : 'Mismatch';
  const verdictBadgeClass =
    isMatch == null
      ? 'bg-slate-100 text-slate-700 ring-slate-200'
      : isMatch
        ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
        : 'bg-rose-50 text-rose-700 ring-rose-200';
  const panelClass =
    isMatch == null
      ? 'border-slate-200 bg-white'
      : isMatch
        ? 'border-emerald-200 bg-emerald-50/40'
        : 'border-rose-200 bg-rose-50/40';

  return (
    <div className="space-y-4 pb-2">
      <section className={`rounded-2xl border p-4 ${panelClass}`}>
        <div className="flex items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-slate-900">Diff</h4>
          <Badge className={verdictBadgeClass}>{verdictLabel}</Badge>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <StatCard
            label="Agent Response Is ESI-1"
            value={isEsi1 == null ? '—' : isEsi1 ? 'True' : 'False'}
            tone={isMatch == null ? 'default' : isMatch ? 'positive' : 'danger'}
          />
          <StatCard label="Confidence" value={formatConfidence(confidence)} tone="accent" />
          <StatCard
            label="Expected Acuity"
            value={expectedAcuity == null ? '—' : formatInteger(expectedAcuity)}
            tone={isMatch == null ? 'default' : isMatch ? 'positive' : 'danger'}
          />
        </div>
      </section>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
          Raw Diff JSON
        </summary>
        <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <JsonInspector value={diff} />
        </div>
      </details>
    </div>
  );
}

const DIFF_RENDERERS: Record<string, DiffRenderer> = {
  esiagent: renderEsiDiff,
  esitriageagent: renderEsiDiff,
};

function resolveDiffRenderer(agentName: string) {
  const normalized = normalizeAgentName(agentName);
  const directRenderer = DIFF_RENDERERS[normalized];
  if (directRenderer) return directRenderer;
  if (normalized.includes('esi')) return renderEsiDiff;
  return renderGenericDiff;
}

export default function AgentTestRunDrawer({
  agentName,
  runId,
  selectedCases,
  error,
  onStart,
}: AgentTestRunDrawerProps) {
  const harnessTabsId = useId();
  const viewerTabsId = useId();
  const modelSelectId = useId();
  const [activeHarnessTab, setActiveHarnessTab] = useState<HarnessTabKey>('cases');
  const [activeViewerTab, setActiveViewerTab] = useState<ViewerTabKey>('case_details');
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [caseStates, setCaseStates] = useState<Record<string, { status: CaseStatus }>>({});
  const [runMetrics, setRunMetrics] = useState<RunMetrics | null>(null);
  const [runPhase, setRunPhase] = useState<RunPhase>('idle');
  const [agentRunByCaseId, setAgentRunByCaseId] = useState<Record<string, string>>({});

  const [outputsByCaseId, setOutputsByCaseId] = useState<Record<string, CaseOutputState>>({});
  const [metricsByCaseId, setMetricsByCaseId] = useState<Record<string, CaseMetricsState>>({});
  const [diffByCaseId, setDiffByCaseId] = useState<Record<string, CaseDiffState>>({});

  const { models, status: modelsStatus, selectedModelId, setSelectedModelId } = useModels();

  const totals = useMemo(() => {
    const total = selectedCases.length;
    const completed = Object.values(caseStates).filter(
      (c) => c.status === 'passed' || c.status === 'failed',
    ).length;
    const running = Object.values(caseStates).filter((c) => c.status === 'running').length;
    return { total, completed, running, queued: Math.max(total - completed - running, 0) };
  }, [caseStates, selectedCases.length]);


  const insertDiff = useCallback((caseId: string, agentRunId: string | undefined, diff: Record<string, unknown>) => {

    try {
      setDiffByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: 'ready',
          agentRunId,
          diff,
        },
      }));
    } catch (e: unknown) {
      setDiffByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: 'error',
          agentRunId,
          error: e instanceof Error ? e.message : 'Failed to load diff',
        },
      }));
    }
    
  }, []);

  const fetchCaseOutputAndMetrics = useCallback(
    async (caseId: string, agentRunId: string) => {
      if (!agentRunId || !caseId) return;

      try {
        const run = await agentRunService.getAgentRun(agentRunId);
        setOutputsByCaseId((prev) => {
          return {
            ...prev,
            [caseId]: {
              status: 'ready',
              agentRunId,
              output: run.outputJson ?? null,
            },
          };
        });
      }
      catch (e: unknown) {
        setOutputsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'error',
            agentRunId,
            error: e instanceof Error ? e.message : 'Failed to load output',
          },
        }));
      }

      try {
        const metrics = await agentRunService.getAgentRunMetrics(agentRunId);
        setMetricsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'ready',
            agentRunId,
            metrics: metrics,
          },
        }));
      }
      catch (e: unknown) {
        setMetricsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'error',
            agentRunId,
            error: e instanceof Error ? e.message : 'Failed to load metrics',
          },
        }));
      }
    },
    [],
  );

  useEffect(() => {
    const initial: Record<string, { status: CaseStatus }> = {};
    for (const c of selectedCases) initial[c.id] = { status: 'pending' };
    setCaseStates(initial);
    setActiveCaseId(selectedCases[0]?.id ?? null);
    setRunMetrics(null);
    setRunPhase(runId ? 'running' : 'idle');
    setAgentRunByCaseId({});
    setOutputsByCaseId({});
    setMetricsByCaseId({});
    setDiffByCaseId({});
    setActiveViewerTab('case_details');
    setActiveHarnessTab('cases');
  }, [selectedCases, runId]);

  useEffect(() => {
    if (!runId) return undefined;

    const caseRunMap: Record<string, string> = {};
    const url = `${API_BASE_URL}/api/tests/runs/${encodeURIComponent(runId)}/stream`;
    const source = new EventSource(url);
    setRunPhase('running');

    const handleCaseStartPayload = (payload: Record<string, unknown>) => {
      const caseId = extractCaseId(payload);
      const agentRunId = extractAgentRunId(payload);
      if (!caseId || !agentRunId) return;

      caseRunMap[caseId] = agentRunId;
      setAgentRunByCaseId((prev) => ({ ...prev, [caseId]: agentRunId }));
      setCaseStates((prev) => ({
        ...prev,
        [caseId]: { ...(prev[caseId] ?? { status: 'pending' }), status: 'running' },
      }));
      setOutputsByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: prev[caseId]?.status === 'ready' ? 'ready' : 'idle',
          agentRunId,
          output: prev[caseId]?.output,
          error: prev[caseId]?.error,
        },
      }));
      setMetricsByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: prev[caseId]?.status === 'ready' ? 'ready' : 'idle',
          agentRunId,
          metrics: prev[caseId]?.metrics,
          error: prev[caseId]?.error,
        },
      }));
      setDiffByCaseId((prev) => ({
        ...prev,
        [caseId]: {
          status: prev[caseId]?.status === 'ready' ? 'ready' : 'idle',
          agentRunId,
          diff: prev[caseId]?.diff,
          error: prev[caseId]?.error,
        },
      }));
      setActiveCaseId((current) => current ?? caseId);
    };

    const handleCaseDonePayload = (payload: Record<string, unknown>) => {
      const caseId = extractCaseId(payload);
      if (!caseId) return;

      const passed = extractPassed(payload);
      setCaseStates((prev) => ({
        ...prev,
        [caseId]: {
          ...(prev[caseId] ?? { status: 'pending' }),
          status: passed ? 'passed' : 'failed',
        },
      }));

      const agentRunId = extractAgentRunId(payload) ?? caseRunMap[caseId];
      if (!agentRunId) {
        setOutputsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'error',
            error: 'Agent run id not available for this test case.',
          },
        }));
        setMetricsByCaseId((prev) => ({
          ...prev,
          [caseId]: {
            status: 'error',
            error: 'Agent run id not available for this test case.',
          },
        }));
        return;
      }

      caseRunMap[caseId] = agentRunId;
      setAgentRunByCaseId((prev) => ({ ...prev, [caseId]: agentRunId }));
      void fetchCaseOutputAndMetrics(caseId, agentRunId);
    };

    const handleRunDonePayload = (payload: Record<string, unknown>) => {
      const metrics = extractMetrics(payload);
      if (metrics) setRunMetrics(metrics);
      setRunPhase('done');
    };

    const parseEventPayload = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as unknown;
        return isRecord(parsed) ? parsed : null;
      } catch {
        return null;
      }
    };

    source.addEventListener('case_start', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      if (!payload) return;
      handleCaseStartPayload(payload);
    });

    source.addEventListener('case_done', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      if (!payload) return;
      const caseId = extractCaseId(payload);
      if (!caseId) return;
      const agentRunId = extractAgentRunId(payload) ?? caseRunMap[caseId];
      const diff = extractDiff(payload);
      if (diff) insertDiff(caseId, agentRunId, diff);
      handleCaseDonePayload(payload);
    });

    source.addEventListener('run_done', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      console.log(payload);
      if (!payload) return;
      handleRunDonePayload(payload);
    });

    // Some servers emit only generic messages with an "event_type" field.
    source.addEventListener('message', (event) => {
      const payload = parseEventPayload(event as MessageEvent<string>);
      if (!payload) return;


      const eventType =
        asString(payload.event_type) ??
        (isRecord(payload.result) ? asString(payload.result.event_type) : undefined) ??
        (isRecord(payload.payload_json) ? asString(payload.payload_json.event_type) : undefined);

      if (eventType === 'case_start') handleCaseStartPayload(payload);
      if (eventType === 'case_done') {
        const caseId = extractCaseId(payload);
        if (caseId) {
          const agentRunId = extractAgentRunId(payload) ?? caseRunMap[caseId];
          const diff = extractDiff(payload);
          if (diff) insertDiff(caseId, agentRunId, diff);
        }
        handleCaseDonePayload(payload);
      }
      if (eventType === 'run_done') handleRunDonePayload(payload);
    });

    source.addEventListener('done', () => {
      setRunPhase('done');
      source.close();
    });

    // Keep native EventSource retry behavior; mark state for visibility.
    source.onerror = () => {
      setRunPhase((prev) => (prev === 'running' ? 'running' : prev));
    };

    return () => {
      source.close();
    };
  }, [runId, fetchCaseOutputAndMetrics, insertDiff]);

  const activeCase = useMemo(
    () => selectedCases.find((c) => c.id === activeCaseId),
    [selectedCases, activeCaseId],
  );

  const activeAgentRunId = activeCaseId ? agentRunByCaseId[activeCaseId] ?? null : null;
  const activeOutputState = activeCaseId ? outputsByCaseId[activeCaseId] : undefined;
  const activeMetricsState = activeCaseId ? metricsByCaseId[activeCaseId] : undefined;
  const activeDiffState = activeCaseId ? diffByCaseId[activeCaseId] : undefined;
  const activeCaseStatus = activeCaseId ? caseStates[activeCaseId]?.status : undefined;
  const activeMetricsRecord =
    activeMetricsState?.status === 'ready' && isRecord(activeMetricsState.metrics)
      ? activeMetricsState.metrics
      : null;
  const activeDiffRecord =
    activeDiffState?.status === 'ready' && isRecord(activeDiffState.diff)
      ? activeDiffState.diff
      : null;
  const activeOutputRecord =
    activeOutputState?.status === 'ready' && isRecord(activeOutputState.output)
      ? activeOutputState.output
      : null;
  const diffRenderer = useMemo(() => resolveDiffRenderer(agentName), [agentName]);

  const activeResultView = useMemo<CaseResultViewModel | null>(() => {
    if (!activeOutputRecord) return null;

    const decisionRaw = getValueByAliases(activeOutputRecord, RESULT_ALIASES.decision);
    const confidenceRaw = getValueByAliases(activeOutputRecord, RESULT_ALIASES.confidence);
    const summaryRaw = getValueByAliases(activeOutputRecord, RESULT_ALIASES.summary);
    const risksRaw = getValueByAliases(activeOutputRecord, RESULT_ALIASES.risks);
    const missingRaw = getValueByAliases(activeOutputRecord, RESULT_ALIASES.missing);
    const justificationRaw = getValueByAliases(activeOutputRecord, RESULT_ALIASES.justification);

    const decisionBool = parseDecision(decisionRaw);
    const decisionLabel =
      decisionBool == null
        ? typeof decisionRaw === 'string'
          ? decisionRaw
          : 'Unknown'
        : decisionBool
          ? 'ESI-1'
          : 'Not ESI-1';
    const decisionTone: CaseResultViewModel['decisionTone'] =
      decisionBool == null ? 'neutral' : decisionBool ? 'positive' : 'danger';

    return {
      decisionLabel,
      decisionTone,
      confidenceLabel: formatConfidence(asNumber(confidenceRaw)),
      caseSummary:
        typeof summaryRaw === 'string' && summaryRaw.trim().length > 0
          ? summaryRaw
          : 'No summary was provided by this case output.',
      justification:
        typeof justificationRaw === 'string' && justificationRaw.trim().length > 0
          ? justificationRaw
          : 'No justification was provided by this case output.',
      risks: toStringArray(risksRaw),
      missingInformation: toStringArray(missingRaw),
    };
  }, [activeOutputRecord]);

  const activeAdditionalOutputEntries = useMemo(() => {
    if (!activeOutputRecord) return [];
    const known = new Set(
      [
        ...RESULT_ALIASES.decision,
        ...RESULT_ALIASES.confidence,
        ...RESULT_ALIASES.summary,
        ...RESULT_ALIASES.risks,
        ...RESULT_ALIASES.missing,
        ...RESULT_ALIASES.justification,
      ].map(normalizeKey),
    );
    return Object.entries(activeOutputRecord).filter(([key]) => !known.has(normalizeKey(key)));
  }, [activeOutputRecord]);

  function harnessTabId(key: HarnessTabKey) {
    return `${harnessTabsId}-tab-${key}`;
  }

  function harnessPanelId(key: HarnessTabKey) {
    return `${harnessTabsId}-panel-${key}`;
  }

  function viewerTabId(key: ViewerTabKey) {
    return `${viewerTabsId}-tab-${key}`;
  }

  function viewerPanelId(key: ViewerTabKey) {
    return `${viewerTabsId}-panel-${key}`;
  }

  function handleRetryOutput() {
    if (!activeCaseId) return;
    const agentRunId = activeOutputState?.agentRunId ?? activeAgentRunId;
    if (!agentRunId) return;
    void fetchCaseOutputAndMetrics(activeCaseId, agentRunId);
  }

  const summaryTotal = runMetrics?.total ?? totals.total;
  const summaryPassed = runMetrics?.passed ?? totals.completed;
  const summaryFailed = runMetrics?.failed ?? Math.max(summaryTotal - summaryPassed, 0);
  const summaryExecFailed = runMetrics?.exec_failed ?? 0;
  const summaryInvalidPred = runMetrics?.invalid_pred ?? 0;
  const summaryPassRate = runMetrics?.pass_rate ?? (summaryTotal > 0 ? summaryPassed / summaryTotal : null);
  const summaryPassRateLabel = formatPercent(summaryPassRate);
  const summaryPassRateTone: StatCardProps['tone'] =
    summaryPassRate == null ? 'default' : summaryPassRate >= 0.8 ? 'positive' : summaryPassRate >= 0.6 ? 'accent' : 'danger';

  const classification = runMetrics?.classification ?? null;
  const tp = classification?.tp ?? 0;
  const tn = classification?.tn ?? 0;
  const fp = classification?.fp ?? 0;
  const fn = classification?.fn ?? 0;
  const confusionMax = Math.max(tp, tn, fp, fn, 1);

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-hidden">
      <SegmentedTabs
        idBase={harnessTabsId}
        tabs={harnessTabs}
        value={activeHarnessTab}
        onChange={setActiveHarnessTab}
        ariaLabel="Test harness tabs"
        className="max-w-sm"
      />
      <span className="sr-only">{agentName}</span>

      <div
        id={harnessPanelId('cases')}
        role="tabpanel"
        aria-labelledby={harnessTabId('cases')}
        hidden={activeHarnessTab !== 'cases'}
        className="h-full min-h-0"
      >
        <div className="grid h-full grid-cols-5 grid-rows-10 overflow-y-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="col-span-3 row-span-10 min-h-0 overflow-auto border-r border-slate-200 pb-6">
            {selectedCases.length ? (
              <div className="divide-y divide-slate-200">
                {selectedCases.map((testCase) => {
                  const status = caseStates[testCase.id]?.status ?? 'pending';
                  const isActive = activeCaseId === testCase.id;
                  return (
                    <button
                      key={testCase.id}
                      type="button"
                      onClick={() => setActiveCaseId(testCase.id)}
                      className={`flex w-full items-center justify-between p-4 text-left transition ${isActive ? 'bg-slate-50' : 'hover:bg-slate-50'
                        }`}
                    >
                      <div className="min-w-0 space-y-1">
                        <p className="truncate text-sm font-semibold text-slate-900">
                          {titleCase(testCase.name)}
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(testCase.inputJson).map(([label, value]) => (
                            <CaseBadge key={label} label={label} value={value as string | number} />
                          ))}
                        </div>
                      </div>
                      <div className="shrink-0">
                        <StatusDot status={status} />
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="p-4 text-xs text-slate-500">No cases selected.</p>
            )}
          </div>

          <div className="col-span-2 row-span-3 border-b border-slate-200 px-6 py-4 text-slate-900">
            <div className="flex flex-wrap items-center justify-between gap-6">
              <div>
                <p className="text-[11px] uppercase tracking-[0.3em] text-slate-900/70">Harness panel</p>
                <h3 className="text-2xl font-semibold">Start Test Run</h3>
                <p className="text-sm text-slate-900/70">
                  {selectedCases.length} case{selectedCases.length === 1 ? '' : 's'} selected
                </p>

                <div className="mt-3 flex items-center gap-2">
                  <label htmlFor={modelSelectId} className="text-xs font-semibold text-slate-700">
                    Model
                  </label>
                  <select
                    id={modelSelectId}
                    value={selectedModelId}
                    onChange={(e) => setSelectedModelId(e.target.value)}
                    disabled={modelsStatus !== 'success' || runPhase === 'running' || models.length === 0}
                    className="min-w-52 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
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
              </div>

              <button
                type="button"
                onClick={() => onStart(selectedModelId || undefined)}
                disabled={runPhase === 'running' || !selectedCases.length}
                className={`inline-flex items-center gap-2 rounded-2xl px-5 py-2 text-xs font-semibold shadow-slate-900/40 backdrop-blur transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-white ${runPhase === 'running'
                  ? 'cursor-not-allowed bg-slate-200 text-slate-600'
                  : 'bg-PrimaryBlue text-white hover:scale-[1.02] hover:bg-PrimaryBlue/90 disabled:cursor-not-allowed disabled:opacity-60'
                  }`}
              >
                <span>{runPhase === 'running' ? 'Running' : runPhase === 'done' ? 'Re Run' : 'Start'}</span>
                <span
                  className={`inline-flex h-2.5 w-2.5 rounded-full ${runPhase === 'running' ? 'bg-orange-400' : 'bg-emerald-400'
                    }`}
                />
              </button>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-4">
              {[
                { label: 'Total cases', value: totals.total },
                { label: 'Running', value: totals.running },
                { label: 'Completed', value: totals.completed },
                { label: 'Queued', value: totals.queued },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-2xl border border-slate-200 bg-white/5 p-3 text-[10px] uppercase tracking-wide text-slate-900/80 backdrop-blur"
                >
                  <p className="text-[10px] font-semibold text-slate-900/60">{stat.label}</p>
                  <p className="text-xl font-semibold">{stat.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-2 row-span-7 min-h-0 overflow-hidden p-4">
            <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-white p-3">
              <SegmentedTabs
                idBase={viewerTabsId}
                tabs={viewerTabs}
                value={activeViewerTab}
                onChange={setActiveViewerTab}
                ariaLabel="Case inspection views"
                className="max-w-md"
              />

              <div className="mt-3 min-h-0 flex-1">
                <div
                  id={viewerPanelId('case_details')}
                  role="tabpanel"
                  aria-labelledby={viewerTabId('case_details')}
                  hidden={activeViewerTab !== 'case_details'}
                  className="h-full min-h-0 overflow-auto"
                >
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs font-semibold text-slate-900">Details</p>
                    {activeCase ? (
                      <div className="mt-2 space-y-2">
                        <p className="text-sm font-semibold text-slate-900">{titleCase(activeCase.name)}</p>
                        <p className="font-mono text-[11px] text-slate-500">{activeCase.id}</p>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(activeCase.inputJson).map(([label, value]) => (
                            <CaseBadge key={label} label={label} value={value as string | number} />
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-600">Select a test case to view details.</p>
                    )}
                  </div>
                </div>

                <div
                  id={viewerPanelId('test_traces')}
                  role="tabpanel"
                  aria-labelledby={viewerTabId('test_traces')}
                  hidden={activeViewerTab !== 'test_traces'}
                  className="h-full min-h-0 overflow-hidden"
                >
                  <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-slate-50 ">
                    <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-100 bg-slate-50 p-3">
                      {activeAgentRunId ? (
                        <AgentTracesComponent runId={activeAgentRunId} />
                      ) : activeCaseId ? (
                        <p className="text-xs text-slate-600">
                          {runPhase === 'running'
                            ? 'Waiting for this case to start streaming traces.'
                            : 'No agent run yet for this case. Start the run to stream traces.'}
                        </p>
                      ) : (
                        <p className="text-xs text-slate-600">Select a test case to view its traces.</p>
                      )}
                    </div>
                  </div>
                </div>

                <div
                  id={viewerPanelId('outputs')}
                  role="tabpanel"
                  aria-labelledby={viewerTabId('outputs')}
                  hidden={activeViewerTab !== 'outputs'}
                  className="h-full min-h-0 overflow-auto"
                >
                  <div className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-slate-50 p-3">

                    {!activeCaseId ? (
                      <p className="text-xs text-slate-600">Select a test case to view its output.</p>
                    ) : activeOutputState?.status === 'loading' ? (
                      <p className="text-xs text-slate-600">Loading output…</p>
                    ) : activeOutputState?.status === 'error' ? (
                      <div className="space-y-3">
                        <p className="text-xs text-rose-700">
                          {activeOutputState.error ?? 'Failed to load output.'}
                        </p>
                        <button
                          type="button"
                          onClick={handleRetryOutput}
                          disabled={!activeOutputState.agentRunId && !activeAgentRunId}
                          className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        >
                          Retry Output Fetch
                        </button>
                      </div>
                    ) : activeOutputState?.status === 'ready' ? (
                      activeOutputRecord && activeResultView ? (
                        <div className="space-y-4 pb-2">
                          <section className="rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,rgba(14,165,233,0.06)_0%,rgba(255,255,255,0.95)_42%,rgba(16,185,129,0.06)_100%)] p-4">
                            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-2">
                              {[
                                {
                                  label: 'Decision',
                                  value: activeResultView.decisionLabel,
                                  tone:
                                    activeResultView.decisionTone === 'positive'
                                      ? 'border-emerald-200 bg-emerald-50/70'
                                      : activeResultView.decisionTone === 'danger'
                                        ? 'border-rose-200 bg-rose-50/70'
                                        : 'border-slate-200 bg-white',
                                },
                                {
                                  label: 'Confidence',
                                  value: activeResultView.confidenceLabel,
                                  tone: 'border-sky-200 bg-sky-50/70',
                                }
                              ].map((card) => (
                                <div key={card.label} className={`rounded-xl border p-3 ${card.tone}`}>
                                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                                    {card.label}
                                  </p>
                                  <p className="mt-1 text-base font-semibold text-slate-900 break-all">
                                    {card.value}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </section>

                          <section className="grid gap-4 xl:grid-cols-2">
                            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                              <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Clinical Summary
                              </h5>
                              <p className="mt-2 text-sm leading-relaxed text-slate-800">
                                {activeResultView.caseSummary}
                              </p>
                            </div>

                            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                              <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Justification
                              </h5>
                              <p className="mt-2 text-sm leading-relaxed text-slate-800">
                                {activeResultView.justification}
                              </p>
                            </div>

                            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                              <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Key Risks
                              </h5>
                              {activeResultView.risks.length ? (
                                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-800">
                                  {activeResultView.risks.map((risk, index) => (
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
                              {activeResultView.missingInformation.length ? (
                                <div className="mt-2 flex flex-wrap gap-2">
                                  {activeResultView.missingInformation.map((item, index) => (
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

                          {activeAdditionalOutputEntries.length ? (
                            <details className="rounded-2xl border border-slate-200 bg-white p-4">
                              <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
                                Additional Output Fields
                              </summary>
                              <div className="mt-3 grid gap-3 md:grid-cols-2">
                                {activeAdditionalOutputEntries.map(([key, item]) => (
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
                              <JsonInspector value={activeOutputRecord} />
                            </div>
                          </details>
                        </div>
                      ) : (
                        <p className="text-xs text-slate-600">No output returned for this case.</p>
                      )
                    ) : activeCaseStatus === 'passed' || activeCaseStatus === 'failed' ? (
                      <p className="text-xs text-slate-600">
                        Output not available yet for this case. You can retry fetching it.
                      </p>
                    ) : (
                      <p className="text-xs text-slate-600">
                        Output will appear once this case finishes running.
                      </p>
                    )}
                  </div>
                </div>

                <div
                  id={viewerPanelId('diff')}
                  role="tabpanel"
                  aria-labelledby={viewerTabId('diff')}
                  hidden={activeViewerTab !== 'diff'}
                  className="h-full min-h-0 overflow-auto"
                >
                  {!activeCaseId ? (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                      Select a test case to view its diff.
                    </div>
                  ) : activeDiffState?.status === 'loading' ? (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                      Loading diff…
                    </div>
                  ) : activeDiffState?.status === 'error' ? (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                      {activeDiffState.error}
                    </div>
                  ) : activeDiffState?.status === 'ready' && activeDiffRecord ? (
                    diffRenderer(activeDiffRecord)
                  ) : activeCaseStatus === 'passed' || activeCaseStatus === 'failed' ? (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                      Diff not available for this case.
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                      Diff will appear once this case finishes running.
                    </div>
                  )}
                </div>

                <div
                  id={viewerPanelId('metrics')}
                  role="tabpanel"
                  aria-labelledby={viewerTabId('metrics')}
                  hidden={activeViewerTab !== 'metrics'}
                  className="h-full min-h-0 overflow-auto"
                >
                  {activeMetricsState?.status === 'loading' ? (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                      Loading metrics…
                    </div>
                  ) : activeMetricsState?.status === 'error' ? (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                      {activeMetricsState.error}
                    </div>
                  ) : activeMetricsState?.status === 'ready' ? (
                    <div className="space-y-4 pb-2">
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
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
                          />
                        </div>

                        <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
                          <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-slate-600">
                            Raw Metrics JSON
                          </summary>
                          <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-white p-3">
                            <JsonInspector value={activeMetricsState.metrics} />
                          </div>
                        </details>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        id={harnessPanelId('results')}
        role="tabpanel"
        aria-labelledby={harnessTabId('results')}
        hidden={activeHarnessTab !== 'results'}
        className="h-full min-h-0 overflow-auto"
      >
        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {!runId && runPhase === 'idle' ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Test not run. Please start a test run.
          </div>
        ) : runPhase === 'running' ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Currently running test…
          </div>
        ) : runPhase === 'done' ? (
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
                <StatCard
                  label="Exec Failed"
                  value={formatInteger(summaryExecFailed)}
                  tone={summaryExecFailed > 0 ? 'danger' : 'default'}
                />
                <StatCard
                  label="Invalid Pred"
                  value={formatInteger(summaryInvalidPred)}
                  tone={summaryInvalidPred > 0 ? 'danger' : 'default'}
                />
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
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Confusion Matrix</p>
                    <div className="mt-2 grid grid-cols-[5.5rem_1fr_1fr] gap-2">
                      <div />
                      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                        Predicted Positive
                      </div>
                      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                        Predicted Negative
                      </div>

                      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                        Actual Positive
                      </div>
                      <ConfusionCell label="TP" value={tp} tone="correct" maxValue={confusionMax} />
                      <ConfusionCell label="FN" value={fn} tone="error" maxValue={confusionMax} />

                      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                        Actual Negative
                      </div>
                      <ConfusionCell label="FP" value={fp} tone="error" maxValue={confusionMax} />
                      <ConfusionCell label="TN" value={tn} tone="correct" maxValue={confusionMax} />
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Excluded</p>
                    <div className="mt-3 space-y-2">
                      <StatCard
                        label="Exec Failed"
                        value={formatInteger(classification.excluded?.exec_failed ?? null)}
                        tone={(classification.excluded?.exec_failed ?? 0) > 0 ? 'danger' : 'default'}
                      />
                      <StatCard
                        label="Invalid Pred"
                        value={formatInteger(classification.excluded?.invalid_pred ?? null)}
                        tone={(classification.excluded?.invalid_pred ?? 0) > 0 ? 'danger' : 'default'}
                      />
                      <StatCard
                        label="Other"
                        value={formatInteger(classification.excluded?.other ?? null)}
                        tone={(classification.excluded?.other ?? 0) > 0 ? 'danger' : 'default'}
                      />
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
                <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
                  Raw Run Metrics JSON
                </summary>
                <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <JsonInspector value={runMetrics} />
                </div>
              </details>
            ) : null}
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Results not available yet.
          </div>
        )}
      </div>
    </div>
  );
}
