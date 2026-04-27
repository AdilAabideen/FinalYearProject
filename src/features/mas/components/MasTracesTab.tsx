import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { EventStreamPayload, SwarmEventType } from '../../../types/masRuns';
import type { ActiveHandoffEdges, AgentRunningStatus, BoundaryEdgeHighlights } from './MasDetailSplitView';
import { AgentTracesComponent } from '../../agents/components/AgentTracesComponent';
import JsonRenderer from './JsonRenderer';
import type { AgentRunMetrics } from '../../../types/agentRuns';
import { agentRunService } from '../../../services/agentRunService';
import { Badge } from '../../../shared/ui/Badge';
import { AgentStatCard as StatCard } from '../../agents/components/shared/AgentStatCard';
import { AgentRawJsonDetails } from '../../agents/components/shared/AgentRawJsonDetails';
import { AgentReliabilitySummaryPanel } from '../../agents/components/shared/AgentReliabilitySummaryPanel';
import { formatCurrency, formatDuration, formatInteger } from '../../agents/utils/format';
import { asNumber } from '../../agents/utils/runResult';
import { getReliabilitySummaryView } from '../../agents/utils/reliability';

type MasTracesTabProps = {
  agentNames: string[];
  eventsStreamUrl: string;
  swarm_run_id: string;
  setAgentStatus: Dispatch<SetStateAction<AgentRunningStatus>>;
  setActiveHandoffEdges: Dispatch<SetStateAction<ActiveHandoffEdges>>;
  setBoundaryEdgeHighlights: Dispatch<SetStateAction<BoundaryEdgeHighlights>>;
  onMasDone: () => Promise<void>;
};

type MasEventTypes =
  | 'Swarm Started'
  | 'Swarm Ended'
  | 'Agent Execution Started'
  | 'Agent Execution Finished'
  | 'Swarm Error'
  | 'Handoff'
  | 'Gate Evaluated'
  | 'Final Output Created';
type ArchType = 'MAS' | 'Agent';

type MasGeneralEvents = {
  event_type: MasEventTypes;
  arch_type: ArchType;
  description: string;
  created_at: string;
};

type AgentPanelProps = {
  activeAgentName: string;
  activeAgentRunId: string | null;
  activeAgentOutput: unknown;
  activeMetricsState: MetricsState;
  selectedTab: Tabs;
  setSelectedTab: Dispatch<SetStateAction<Tabs>>;
};

type MetricsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; metrics: AgentRunMetrics };

type GeneralPanelProps = {
  swarmRunId: string;
  streamState: string;
  generalEvents: MasGeneralEvents[];
  agentCount: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asNullableString(value: unknown): string | null {
  return typeof value === 'string' ? value : value === null ? null : null;
}

function asEventType(value: unknown): SwarmEventType | null {
  if (
    value === 'swarm_started' ||
    value === 'swarm_failed' ||
    value === 'agent_started' ||
    value === 'handoff_created' ||
    value === 'agent_completed' ||
    value === 'gate_evaluated' ||
    value === 'final_output_created' ||
    value === 'swarm_completed'
  ) {
    return value;
  }
  return null;
}

function parseEventStreamPayload(value: unknown): EventStreamPayload | null {
  if (!isRecord(value)) return null;

  const eventType = asEventType(value.event_type);
  if (!eventType) return null;
  if (typeof value.id !== 'number') return null;
  if (typeof value.swarm_run_id !== 'string') return null;
  if (typeof value.seq !== 'number') return null;
  if (typeof value.workflow_id !== 'string') return null;
  if (typeof value.created_at !== 'string') return null;

  return {
    id: value.id,
    swarm_run_id: value.swarm_run_id,
    seq: value.seq,
    event_type: eventType,
    workflow_id: value.workflow_id,
    agent_run_id: asNullableString(value.agent_run_id),
    agent_name: asNullableString(value.agent_name),
    handoff_id: asNullableString(value.handoff_id),
    gate_evaluation_id: asNullableString(value.gate_evaluation_id),
    final_output_id: asNullableString(value.final_output_id),
    status: typeof value.status === 'string' ? value.status : '',
    payload_json: isRecord(value.payload_json) ? value.payload_json : null,
    payload_text: asNullableString(value.payload_text),
    created_at: value.created_at,
  };
}

function buildInitialAgentRunIds(agentNames: string[]) {
  const next: Record<string, string | null> = {};
  for (const agentName of agentNames) next[agentName] = null;
  return next;
}

function appendGeneralEvent(
  setGeneralEvents: Dispatch<SetStateAction<MasGeneralEvents[]>>,
  event: MasGeneralEvents,
) {
  setGeneralEvents((prev) => [...prev, event]);
}

function formatAgentName(agentName: string) {
  return agentName
    .replace(/_agent$/, '')
    .replace('general', 'General')
    .replace('esi345', 'ESI3,4,5')
    .replace('esi2', 'ESI2')
    .replace('esi1', 'ESI1')
    .replace('vitals', 'Vitals')
    .replace('doctor', 'Doctor');
}

function formatTraceTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function normalizeOutputValue(value: unknown) {
  if (value == null) return null;
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }

  return value;
}

type tabKey = 'traces' | 'output' | "metrics"

type Tabs = {
  key: tabKey,
  name: string
}

const tabs: Tabs[] = [
  {
    key: "traces",
    name: "Traces"
  },
  {
    key: "output",
    name: "Output"
  },
  {
    key: "metrics",
    name: "Metrics"
  }
]

const IDLE_METRICS_STATE: MetricsState = { status: 'idle' };

function AgentPanel({
  activeAgentName,
  activeAgentRunId,
  activeAgentOutput,
  activeMetricsState,
  selectedTab,
  setSelectedTab,
}: AgentPanelProps) {
  const normalizedOutput = normalizeOutputValue(activeAgentOutput);

  function viewerTabId(key: tabKey) {
    return `${activeAgentName}-${key}-tab`;
  }

  function viewerPanelId(key: tabKey) {
    return `${activeAgentName}-${key}-panel`;
  }

  const activeMetricsRecord = activeMetricsState.status === 'ready' ? activeMetricsState.metrics : null;
  const activeReliabilitySummaryView = getReliabilitySummaryView(activeMetricsRecord, {
    fallbackCountsToZero: true,
  });
  const activeCaseStatus = activeMetricsRecord?.status ?? null;

  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-white">
      <div className="shrink-0 border-b border-slate-200 px-4 py-3">
        <p className="text-base font-semibold text-slate-900">{formatAgentName(activeAgentName)}</p>
        <p className="mt-1 text-xs font-medium text-slate-500">{activeAgentName}</p>
      </div>

      <div className="flex w-full border-b border-slate-200">
        {tabs.map((tab) => {
          const active = selectedTab.key === tab.key;

          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setSelectedTab(tab)}
              id={viewerTabId(tab.key)}
              role="tab"
              aria-selected={active}
              aria-controls={viewerPanelId(tab.key)}
              className={[
                'border-r cursor-pointer border-slate-200 px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-slate-100 text-slate-900'
                  : 'bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900',
              ].join(' ')}
            >
              {tab.name}
            </button>
          );
        })}
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {selectedTab.key === 'traces' ? (
          activeAgentRunId ? (
            <div
              id={viewerPanelId('traces')}
              role="tabpanel"
              aria-labelledby={viewerTabId('traces')}
              className="h-full min-h-0 overflow-hidden p-3 pb-20"
            >
              <AgentTracesComponent runId={activeAgentRunId} />
            </div>
          ) : (
            <div className="flex h-full items-start justify-start p-6">
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
                <p className="text-sm font-semibold text-slate-900">Waiting for agent run</p>
                <p className="mt-2 text-sm text-slate-500">
                  Trace output will appear here once this agent starts running.
                </p>
              </div>
            </div>
          )
        ) : selectedTab.key === 'metrics' ? (
          <div
            id={viewerPanelId('metrics')}
            role="tabpanel"
            aria-labelledby={viewerTabId('metrics')}
            className="h-full min-h-0 overflow-auto p-3 pb-20"
          >
            {activeMetricsState.status === 'loading' ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                Loading metrics…
              </div>
            ) : activeMetricsState.status === 'error' ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                {activeMetricsState.error}
              </div>
            ) : activeMetricsState.status === 'ready' ? (
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
                      small={true}
                    />
                  </div>

                  <AgentReliabilitySummaryPanel
                    summaryView={activeReliabilitySummaryView}
                    statusSmall={true}
                  />

                  <AgentRawJsonDetails
                    summary="Raw Metrics JSON"
                    value={activeMetricsState.metrics}
                    className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3"
                    contentClassName="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-white p-3"
                  />
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                Metrics will appear once this agent finishes running.
              </div>
            )}
          </div>
        ) : normalizedOutput ? (
          <div className="h-full min-h-0 overflow-y-auto pb-20">
            <div className="space-y-2">
              <JsonRenderer title="Agent Communication Output" value={normalizedOutput} />
            </div>
          </div>
        ) : (
          <div className="flex h-full items-start justify-start p-6">
            <div className="w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
              <p className="text-sm font-semibold text-slate-900">No Agent Communication</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function GeneralPanel({
  swarmRunId,
  streamState,
  generalEvents,
  agentCount,
}: GeneralPanelProps) {
  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-white">
      <div className="flex w-full shrink-0 flex-col gap-3 border-b border-slate-200 px-5 py-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-1">
            <p className="text-xl font-semibold text-slate-900">General Traces</p>
            <p className="text-xs font-semibold text-slate-600">
              Run ID : <span className="font-mono text-slate-700">{swarmRunId}</span>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            Stream: {streamState}
          </div>
          <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
            Events: {generalEvents.length}
          </div>
          <div className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            Agents: {agentCount}
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 w-full overflow-y-auto px-5 py-4 pb-20">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 py-1">
          {generalEvents.length ? (
            generalEvents.map((event, index) => (
              <div key={`${event.created_at}-${event.event_type}-${index}`} className="space-y-1">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">SWARM EVENT</p>
                  <p className="text-[11px] font-mono text-slate-400">
                    {formatTraceTimestamp(event.created_at)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-slate-900">{event.event_type}</p>
                  <span className="text-xs text-slate-400">•</span>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {event.arch_type}
                  </p>
                </div>
                <p className="max-w-3xl text-sm text-slate-700">{event.description}</p>
              </div>
            ))
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="text-sm font-semibold text-slate-900">Waiting for swarm events</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MasTracesTab({
  agentNames,
  eventsStreamUrl,
  swarm_run_id,
  setAgentStatus,
  setActiveHandoffEdges,
  setBoundaryEdgeHighlights,
  onMasDone,
}: MasTracesTabProps) {
  const normalizedAgentNames = useMemo(
    () => agentNames.filter((name, index, arr) => arr.indexOf(name) === index),
    [agentNames],
  );

  const [activeAgentName, setActiveAgentName] = useState<string>('general');

  const sourceRef = useRef<EventSource | null>(null);
  const onMasDoneRef = useRef(onMasDone);
  const setAgentStatusRef = useRef(setAgentStatus);
  const setActiveHandoffEdgesRef = useRef(setActiveHandoffEdges);
  const setBoundaryEdgeHighlightsRef = useRef(setBoundaryEdgeHighlights);
  const handoffTimeoutsRef = useRef<Record<string, number>>({});
  const metricsAbortRefs = useRef<Record<string, AbortController>>({});
  const boundaryTimeoutsRef = useRef<{ start: number | null; end: number | null }>({
    start: null,
    end: null,
  });
  const [agentRunIds, setAgentRunIds] = useState<Record<string, string | null>>(() =>
    buildInitialAgentRunIds(normalizedAgentNames),
  );
  const [agentOutputs, setAgentOutputs] = useState<Record<string, unknown>>({});
  const [agentMetricsStates, setAgentMetricsStates] = useState<Record<string, MetricsState>>({});
  const [streamState, setStreamState] = useState<string>('waiting');
  const [errorText, setErrorText] = useState<string | null>(null);
  const [generalEvents, setGeneralEvents] = useState<MasGeneralEvents[]>([]);
  const activeAgentRunId =
    activeAgentName && activeAgentName !== 'general' ? agentRunIds[activeAgentName] ?? null : null;
  const activeAgentOutput =
    activeAgentName && activeAgentName !== 'general' ? agentOutputs[activeAgentName] ?? null : null;
  const activeMetricsState: MetricsState =
    activeAgentName && activeAgentName !== 'general'
      ? agentMetricsStates[activeAgentName] ?? IDLE_METRICS_STATE
      : IDLE_METRICS_STATE;

  const triggerBoundaryHighlight = useCallback((type: 'start' | 'end') => {
    const existingTimeout = boundaryTimeoutsRef.current[type];
    if (existingTimeout) window.clearTimeout(existingTimeout);

    const updateBoundaryEdgeHighlights = setBoundaryEdgeHighlightsRef.current;
    updateBoundaryEdgeHighlights((prev) => ({ ...prev, [type]: 'active' }));
    boundaryTimeoutsRef.current[type] = window.setTimeout(() => {
      updateBoundaryEdgeHighlights((prev) => ({ ...prev, [type]: 'visited' }));
      boundaryTimeoutsRef.current[type] = null;
    }, 10000);
  }, []);

  const [selectedTab, setSelectedTab] = useState<Tabs>(tabs[0]);

  useEffect(() => {
    onMasDoneRef.current = onMasDone;
  }, [onMasDone]);

  useEffect(() => {
    setAgentStatusRef.current = setAgentStatus;
  }, [setAgentStatus]);

  useEffect(() => {
    setActiveHandoffEdgesRef.current = setActiveHandoffEdges;
  }, [setActiveHandoffEdges]);

  useEffect(() => {
    setBoundaryEdgeHighlightsRef.current = setBoundaryEdgeHighlights;
  }, [setBoundaryEdgeHighlights]);

  useEffect(() => {
    setAgentRunIds((prev) => {
      const next = buildInitialAgentRunIds(normalizedAgentNames);
      for (const agentName of normalizedAgentNames) {
        next[agentName] = prev[agentName] ?? null;
      }
      return next;
    });
  }, [normalizedAgentNames]);

  useEffect(() => {
    return () => {
      for (const timeoutId of Object.values(handoffTimeoutsRef.current)) {
        window.clearTimeout(timeoutId);
      }
      handoffTimeoutsRef.current = {};
      for (const controller of Object.values(metricsAbortRefs.current)) {
        controller.abort();
      }
      metricsAbortRefs.current = {};
      if (boundaryTimeoutsRef.current.start) window.clearTimeout(boundaryTimeoutsRef.current.start);
      if (boundaryTimeoutsRef.current.end) window.clearTimeout(boundaryTimeoutsRef.current.end);
      boundaryTimeoutsRef.current = { start: null, end: null };
    };
  }, []);

  const handleOpen = useCallback(() => {
    setStreamState('open');
    setErrorText(null);
  }, []);

  const handleError = useCallback(() => {
    setErrorText('Error');
    setStreamState('waiting');
  }, []);

  const getAgentMetrics = useCallback(async (agentName: string, runId: string) => {
    metricsAbortRefs.current[agentName]?.abort();

    const ac = new AbortController();
    metricsAbortRefs.current[agentName] = ac;

    setAgentMetricsStates((prev) => ({
      ...prev,
      [agentName]: { status: 'loading' },
    }));

    try {
      const metrics = await agentRunService.getAgentRunMetrics(runId, ac.signal);
      if (ac.signal.aborted) return;

      setAgentMetricsStates((prev) => ({
        ...prev,
        [agentName]: { status: 'ready', metrics },
      }));
    } catch (error) {
      if (ac.signal.aborted) return;
      console.error(error);
      setAgentMetricsStates((prev) => ({
        ...prev,
        [agentName]: {
          status: 'error',
          error: error instanceof Error ? error.message : 'Failed to load metrics',
        },
      }));
    } finally {
      if (metricsAbortRefs.current[agentName] === ac) {
        delete metricsAbortRefs.current[agentName];
      }
    }
  }, []);

  const handleSwarmEvent = useCallback((event: MessageEvent<string>) => {
    try {
      const raw = JSON.parse(event.data) as unknown;
      const parsed = parseEventStreamPayload(raw);
      if (!parsed) {
        setErrorText('Invalid stream payload');
        return;
      }

      switch (parsed.event_type) {
        case 'swarm_started': {
          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Swarm Started',
            arch_type: 'MAS',
            description: 'Swarm has started.',
            created_at: parsed.created_at,
          });
          triggerBoundaryHighlight('start');
          break;
        }

        case 'swarm_completed': {
          setStreamState('done');
          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Swarm Ended',
            arch_type: 'MAS',
            description: 'Swarm completed successfully.',
            created_at: parsed.created_at,
          });
          triggerBoundaryHighlight('end');
          break;
        }

        case 'swarm_failed': {
          setErrorText('Swarm failed');
          setStreamState('error');
          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Swarm Error',
            arch_type: 'MAS',
            description: 'Swarm failed.',
            created_at: parsed.created_at,
          });
          break;
        }

        case 'agent_started': {
          const agentName = parsed.agent_name;
          const agentRunId = parsed.agent_run_id;

          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Agent Execution Started',
            arch_type: 'Agent',
            description: `${agentName ?? 'Agent'} started execution.`,
            created_at: parsed.created_at,
          });

          if (agentName) {
            setAgentRunIds((prev) => ({
              ...prev,
              [agentName]: agentRunId,
            }));

            setAgentStatusRef.current((prev) => {
              return {
                ...prev,
                [agentName]: "running"
              }
            })
          }
          break;
        }

        case 'agent_completed': {
          const agentName = parsed.agent_name;
          const agentRunId = parsed.agent_run_id;

          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Agent Execution Finished',
            arch_type: 'Agent',
            description: `${agentName ?? 'Agent'} finished execution.`,
            created_at: parsed.created_at,
          });

          if (agentName) {
            setAgentRunIds((prev) => ({
              ...prev,
              [agentName]: agentRunId,
            }));

            setAgentStatusRef.current((prev) => {
              return {
                ...prev,
                [agentName]: "executed"
              }
            });

            if (agentRunId) {
              void getAgentMetrics(agentName, agentRunId);
            }
          }

          break;
        }

        case 'handoff_created': {
          const fromAgent =
            parsed.payload_json && typeof parsed.payload_json.from_agent === 'string'
              ? parsed.payload_json.from_agent
              : 'unknown agent';

          const toAgent =
            parsed.payload_json && typeof parsed.payload_json.target_agent === 'string'
              ? parsed.payload_json.target_agent
              : 'unknown agent';

          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Handoff',
            arch_type: 'Agent',
            description: `Handoff between ${fromAgent} and ${toAgent}.`,
            created_at: parsed.created_at,
          });

          if (fromAgent !== 'unknown agent' && toAgent !== 'unknown agent') {
            const edgeKey = `${fromAgent}->${toAgent}`;
            const existingTimeout = handoffTimeoutsRef.current[edgeKey];
            if (existingTimeout) window.clearTimeout(existingTimeout);
            const updateActiveHandoffEdges = setActiveHandoffEdgesRef.current;

            if (parsed.payload_json && 'payload' in parsed.payload_json) {
              setAgentOutputs((prev) => ({
                ...prev,
                [fromAgent]: parsed.payload_json?.payload,
              }));
            }

            updateActiveHandoffEdges((prev) => ({
              ...prev,
              [edgeKey]: 'active',
            }));

            setAgentStatusRef.current((prev) => {
              return {
                ...prev,
                [fromAgent]: "executed",
                [toAgent]: "running"
              }
            })

            handoffTimeoutsRef.current[edgeKey] = window.setTimeout(() => {
              updateActiveHandoffEdges((prev) => ({
                ...prev,
                [edgeKey]: 'visited',
              }));
              delete handoffTimeoutsRef.current[edgeKey];
            }, 10000);
          }
          break;
        }
        case 'gate_evaluated': {
          const satisfiedSources =
            parsed.payload_json && Array.isArray(parsed.payload_json.satisfied_sources)
              ? parsed.payload_json.satisfied_sources.filter(
                (value): value is string => typeof value === 'string',
              )
              : ['Unknown Source'];

          const missingSources =
            parsed.payload_json && Array.isArray(parsed.payload_json.missing_sources)
              ? parsed.payload_json.missing_sources.filter(
                (value): value is string => typeof value === 'string',
              )
              : ['Unknown Source'];

          if (missingSources.length == 0) {
            appendGeneralEvent(setGeneralEvents, {
              event_type: 'Gate Evaluated',
              arch_type: 'MAS',
              description: `All Sources Satisfied`,
              created_at: parsed.created_at,
            });
          } else {
            appendGeneralEvent(setGeneralEvents, {
              event_type: 'Gate Evaluated',
              arch_type: 'MAS',
              description: `Gate evaluated. Missing sources: ${missingSources.join(', ')}
          Satisfied sources: ${satisfiedSources.join(', ')}`,
              created_at: parsed.created_at,
            });
          }
          break;
        }
        case 'final_output_created': {
          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Final Output Created',
            arch_type: 'MAS',
            description: 'MAS output finished.',
            created_at: parsed.created_at,
          });
          break;
        }
        default: {
          break;
        }
      }
    } catch (error) {
      setErrorText('Error Occured');
      console.error(error);
    }
  }, [getAgentMetrics, triggerBoundaryHighlight]);

  const handleDone = useCallback((event: MessageEvent<string>) => {
    void event;
    setStreamState('done');
    triggerBoundaryHighlight('end');
    sourceRef.current?.close();
    void onMasDoneRef.current().catch((error: unknown) => {
      console.error('Failed to fetch MAS final output', error);
    });
  }, [triggerBoundaryHighlight]);


  useEffect(() => {
    sourceRef.current?.close();
    for (const timeoutId of Object.values(handoffTimeoutsRef.current)) {
      window.clearTimeout(timeoutId);
    }
    handoffTimeoutsRef.current = {};
    if (boundaryTimeoutsRef.current.start) window.clearTimeout(boundaryTimeoutsRef.current.start);
    if (boundaryTimeoutsRef.current.end) window.clearTimeout(boundaryTimeoutsRef.current.end);
    boundaryTimeoutsRef.current = { start: null, end: null };

    if (!eventsStreamUrl) {
      setGeneralEvents([]);
      setAgentOutputs({});
      setAgentMetricsStates({});
      setStreamState('waiting');
      setErrorText(null);
      for (const controller of Object.values(metricsAbortRefs.current)) {
        controller.abort();
      }
      metricsAbortRefs.current = {};
      setBoundaryEdgeHighlightsRef.current({ start: 'idle', end: 'idle' });
      return;
    }

    setGeneralEvents([]);
    setAgentOutputs({});
    setAgentMetricsStates({});
    setStreamState('connecting');
    setErrorText(null);

    const source = new EventSource(eventsStreamUrl);
    sourceRef.current = source;

    source.onopen = handleOpen;
    source.onerror = handleError;
    source.addEventListener('swarm_event', handleSwarmEvent as EventListener);
    source.addEventListener('done', handleDone as EventListener);

    return () => {
      source.close();
      if (sourceRef.current === source) sourceRef.current = null;
    };
  }, [eventsStreamUrl, handleDone, handleError, handleOpen, handleSwarmEvent]);



  return (
    <div className="grid h-full w-full grid-cols-5 grid-rows-1">
      <div className="col-span-1 h-full border-r border-slate-300 bg-slate-100/60">
        <button
          type="button"
          onClick={() => setActiveAgentName("general")}
          className={[
            'w-full border-b border-slate-300 p-3 text-left text-sm transition-all duration-150 ease-in-out',
            activeAgentName === "general"
              ? 'bg-white font-semibold text-slate-900'
              : 'text-slate-700 hover:bg-slate-50 hover:pl-4 hover:text-slate-900',
          ].join(' ')}
        >
          General
        </button>
        {normalizedAgentNames.map((agentName) => {
          const active = activeAgentName === agentName;

          return (
            <button
              key={agentName}
              type="button"
              onClick={() => setActiveAgentName(agentName)}
              className={[
                'w-full border-b border-slate-300 p-3 text-left text-sm transition-all duration-150 ease-in-out',
                active
                  ? 'bg-white font-semibold text-slate-900'
                  : 'text-slate-700 hover:bg-slate-50 hover:pl-4 hover:text-slate-900',
              ].join(' ')}
            >
              {formatAgentName(agentName)}
            </button>
          );
        })}
      </div>

      <div className="col-span-4 flex h-full min-h-0 w-full flex-col bg-white">
        {errorText ? (
          <div className="border-b border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
            {errorText}
          </div>
        ) : null}
        {activeAgentName === 'general' ? (
          <GeneralPanel
            swarmRunId={swarm_run_id}
            streamState={streamState}
            generalEvents={generalEvents}
            agentCount={normalizedAgentNames.length}
          />
        ) :
          <AgentPanel
            activeAgentName={activeAgentName}
            activeAgentRunId={activeAgentRunId}
            activeAgentOutput={activeAgentOutput}
            activeMetricsState={activeMetricsState}
            selectedTab={selectedTab}
            setSelectedTab={setSelectedTab}
          />
        }
      </div>
    </div>
  );
}
