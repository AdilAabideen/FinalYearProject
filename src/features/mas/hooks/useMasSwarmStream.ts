// Manages use MAS swarm stream behavior.
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { ActiveHandoffEdges, AgentRunningStatus, BoundaryEdgeHighlights } from '../components/MasDetailSplitView';
import { useLatestRef } from './useLatestRef';
import {
  appendGeneralEvent,
  buildInitialAgentRunIds,
  parseEventStreamPayload,
  type MasGeneralEvent,
} from '../utils/masTraces';

type UseMasSwarmStreamArgs = {
  agentNames: string[];
  eventsStreamUrl: string;
  onMasDone: () => Promise<void>;
  setAgentStatus: Dispatch<SetStateAction<AgentRunningStatus>>;
  setActiveHandoffEdges: Dispatch<SetStateAction<ActiveHandoffEdges>>;
  setBoundaryEdgeHighlights: Dispatch<SetStateAction<BoundaryEdgeHighlights>>;
  getAgentMetrics: (agentName: string, runId: string) => Promise<void>;
  resetAgentMetricsStates: () => void;
};

// Manages MAS swarm stream.
export function useMasSwarmStream({
  agentNames,
  eventsStreamUrl,
  onMasDone,
  setAgentStatus,
  setActiveHandoffEdges,
  setBoundaryEdgeHighlights,
  getAgentMetrics,
  resetAgentMetricsStates,
}: UseMasSwarmStreamArgs) {
  const sourceRef = useRef<EventSource | null>(null);
  const handoffTimeoutsRef = useRef<Record<string, number>>({});
  const boundaryTimeoutsRef = useRef<{ start: number | null; end: number | null }>({
    start: null,
    end: null,
  });
  const onMasDoneRef = useLatestRef(onMasDone);
  const setAgentStatusRef = useLatestRef(setAgentStatus);
  const setActiveHandoffEdgesRef = useLatestRef(setActiveHandoffEdges);
  const setBoundaryEdgeHighlightsRef = useLatestRef(setBoundaryEdgeHighlights);

// Manages state.
  const [agentRunIds, setAgentRunIds] = useState<Record<string, string | null>>(() =>
    buildInitialAgentRunIds(agentNames),
  );
  const [agentOutputs, setAgentOutputs] = useState<Record<string, unknown>>({});
  const [streamState, setStreamState] = useState<string>('waiting');
  const [errorText, setErrorText] = useState<string | null>(null);
  const [generalEvents, setGeneralEvents] = useState<MasGeneralEvent[]>([]);

// Manages callback.
  const clearBoundaryTimeouts = useCallback(() => {
    if (boundaryTimeoutsRef.current.start) window.clearTimeout(boundaryTimeoutsRef.current.start);
    if (boundaryTimeoutsRef.current.end) window.clearTimeout(boundaryTimeoutsRef.current.end);
    boundaryTimeoutsRef.current = { start: null, end: null };
  }, []);

// Manages callback.
  const clearHandoffTimeouts = useCallback(() => {
    for (const timeoutId of Object.values(handoffTimeoutsRef.current)) {
      window.clearTimeout(timeoutId);
    }
    handoffTimeoutsRef.current = {};
  }, []);

// Manages callback.
  const triggerBoundaryHighlight = useCallback((type: 'start' | 'end') => {
    const existingTimeout = boundaryTimeoutsRef.current[type];
    if (existingTimeout) window.clearTimeout(existingTimeout);

    const updateBoundaryEdgeHighlights = setBoundaryEdgeHighlightsRef.current;
// Updates boundary edge highlights.
    updateBoundaryEdgeHighlights((prev) => ({ ...prev, [type]: 'active' }));
// Sets timeout.
    boundaryTimeoutsRef.current[type] = window.setTimeout(() => {
// Updates boundary edge highlights.
      updateBoundaryEdgeHighlights((prev) => ({ ...prev, [type]: 'visited' }));
      boundaryTimeoutsRef.current[type] = null;
    }, 10000);
  }, [setBoundaryEdgeHighlightsRef]);

// Manages callback.
  const handleOpen = useCallback(() => {
    setStreamState('open');
    setErrorText(null);
  }, []);

// Manages callback.
  const handleError = useCallback(() => {
    setErrorText('Error');
    setStreamState('waiting');
  }, []);

// Manages callback.
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
// Sets agent run IDS.
            setAgentRunIds((prev) => ({
              ...prev,
              [agentName]: agentRunId,
            }));

// Handles current.
            setAgentStatusRef.current((prev) => ({
              ...prev,
              [agentName]: 'running',
            }));
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
// Sets agent run IDS.
            setAgentRunIds((prev) => ({
              ...prev,
              [agentName]: agentRunId,
            }));

// Handles current.
            setAgentStatusRef.current((prev) => ({
              ...prev,
              [agentName]: 'executed',
            }));

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
// Sets agent outputs.
              setAgentOutputs((prev) => ({
                ...prev,
                [fromAgent]: parsed.payload_json?.payload,
              }));
            }

// Updates active handoff edges.
            updateActiveHandoffEdges((prev) => ({
              ...prev,
              [edgeKey]: 'active',
            }));

// Handles current.
            setAgentStatusRef.current((prev) => ({
              ...prev,
              [fromAgent]: 'executed',
              [toAgent]: 'running',
            }));

// Sets timeout.
            handoffTimeoutsRef.current[edgeKey] = window.setTimeout(() => {
// Updates active handoff edges.
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
// Handles filter.
                (value): value is string => typeof value === 'string',
              )
              : ['Unknown Source'];

          const missingSources =
            parsed.payload_json && Array.isArray(parsed.payload_json.missing_sources)
              ? parsed.payload_json.missing_sources.filter(
// Handles filter.
                (value): value is string => typeof value === 'string',
              )
              : ['Unknown Source'];

          if (missingSources.length === 0) {
            appendGeneralEvent(setGeneralEvents, {
              event_type: 'Gate Evaluated',
              arch_type: 'MAS',
              description: 'All Sources Satisfied',
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
  }, [getAgentMetrics, setActiveHandoffEdgesRef, setAgentStatusRef, triggerBoundaryHighlight]);

// Manages callback.
  const handleDone = useCallback((event: MessageEvent<string>) => {

    void event;
    setStreamState('done');
    triggerBoundaryHighlight('end');
    sourceRef.current?.close();
// Handles catch.
    void onMasDoneRef.current().catch((error: unknown) => {
      console.error('Failed to fetch MAS final output', error);
    });
  }, [onMasDoneRef, triggerBoundaryHighlight]);

// Manages effect.
  useEffect(() => {
// Sets agent run IDS.
    setAgentRunIds((prev) => {
      const next = buildInitialAgentRunIds(agentNames);
      for (const agentName of agentNames) {
        next[agentName] = prev[agentName] ?? null;
      }
      return next;
    });
  }, [agentNames]);

// Manages effect.
  useEffect(() => {
// Manages effect.
    return () => {
      clearHandoffTimeouts();
      clearBoundaryTimeouts();
      resetAgentMetricsStates();
    };
  }, [clearBoundaryTimeouts, clearHandoffTimeouts, resetAgentMetricsStates]);

// Manages effect.
  useEffect(() => {
    sourceRef.current?.close();
    clearHandoffTimeouts();
    clearBoundaryTimeouts();

    if (!eventsStreamUrl) {
      setGeneralEvents([]);
      setAgentOutputs({});
      resetAgentMetricsStates();
      setStreamState('waiting');
      setErrorText(null);
      setBoundaryEdgeHighlightsRef.current({ start: 'idle', end: 'idle' });
      return;
    }

    setGeneralEvents([]);
    setAgentOutputs({});
    resetAgentMetricsStates();
    setStreamState('connecting');
    setErrorText(null);

    const source = new EventSource(eventsStreamUrl);
    sourceRef.current = source;

    source.onopen = handleOpen;
    source.onerror = handleError;
    source.addEventListener('swarm_event', handleSwarmEvent as EventListener);
    source.addEventListener('done', handleDone as EventListener);

// Manages effect.
    return () => {
      source.close();
      if (sourceRef.current === source) sourceRef.current = null;
    };
  }, [
    clearBoundaryTimeouts,
    clearHandoffTimeouts,
    eventsStreamUrl,
    handleDone,
    handleError,
    handleOpen,
    handleSwarmEvent,
    resetAgentMetricsStates,
    setBoundaryEdgeHighlightsRef,
  ]);

  return {
    agentRunIds,
    agentOutputs,
    streamState,
    errorText,
    generalEvents,
  };
}
