import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { ActiveHandoffEdges, AgentRunningStatus, BoundaryEdgeHighlights } from './MasDetailSplitView';
import { agentRunService } from '../../../services/agentRunService';
import { formatMasAgentName } from '../utils/format';
import {
  appendGeneralEvent,
  buildInitialAgentRunIds,
  parseEventStreamPayload,
  type MasGeneralEvent,
} from '../utils/masTraces';
import { MasTracesAgentPanel, type TraceTab } from './MasTracesAgentPanel';
import { type MetricsState } from './MasTracesMetricsPanel';
import { MasTracesGeneralPanel } from './MasTracesGeneralPanel';

type MasTracesTabProps = {
  agentNames: string[];
  eventsStreamUrl: string;
  swarm_run_id: string;
  setAgentStatus: Dispatch<SetStateAction<AgentRunningStatus>>;
  setActiveHandoffEdges: Dispatch<SetStateAction<ActiveHandoffEdges>>;
  setBoundaryEdgeHighlights: Dispatch<SetStateAction<BoundaryEdgeHighlights>>;
  onMasDone: () => Promise<void>;
};

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

const tabs: TraceTab[] = [
  {
    key: 'traces',
    label: 'Traces',
  },
  {
    key: 'output',
    label: 'Output',
  },
  {
    key: 'metrics',
    label: 'Metrics',
  },
];

const IDLE_METRICS_STATE: MetricsState = { status: 'idle' };

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
  const [generalEvents, setGeneralEvents] = useState<MasGeneralEvent[]>([]);
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

  const [selectedTab, setSelectedTab] = useState<TraceTab>(tabs[0]);

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
              {formatMasAgentName(agentName)}
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
          <MasTracesGeneralPanel
            swarmRunId={swarm_run_id}
            streamState={streamState}
            generalEvents={generalEvents}
            agentCount={normalizedAgentNames.length}
          />
        ) :
          <MasTracesAgentPanel
            activeAgentName={activeAgentName}
            activeAgentRunId={activeAgentRunId}
            activeAgentOutput={activeAgentOutput}
            activeMetricsState={activeMetricsState}
            selectedTab={selectedTab}
            setSelectedTab={setSelectedTab}
            tabs={tabs}
            normalizeOutputValue={normalizeOutputValue}
          />
        }
      </div>
    </div>
  );
}
