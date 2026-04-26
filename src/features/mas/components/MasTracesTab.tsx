import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { EventStreamPayload, SwarmEventType } from '../../../types/masRuns';
import type { ActiveHandoffEdges, AgentRunningStatus } from './MasDetailSplitView';

type MasTracesTabProps = {
  agentNames: string[];
  eventsStreamUrl: string;
  swarm_run_id: string;
  setAgentStatus: Dispatch<SetStateAction<AgentRunningStatus>>;
  setActiveHandoffEdges: Dispatch<SetStateAction<ActiveHandoffEdges>>;
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

export default function MasTracesTab({
  agentNames,
  eventsStreamUrl,
  swarm_run_id,
  setAgentStatus,
  setActiveHandoffEdges,
}: MasTracesTabProps) {
  const normalizedAgentNames = useMemo(
    () => agentNames.filter((name, index, arr) => arr.indexOf(name) === index),
    [agentNames],
  );

  const [activeAgentName, setActiveAgentName] = useState<string>('general');

  const sourceRef = useRef<EventSource | null>(null);
  const handoffTimeoutsRef = useRef<Record<string, number>>({});
  const [entries, setEntries] = useState<EventStreamPayload[]>([]);
  const [agentRunIds, setAgentRunIds] = useState<Record<string, string | null>>(() =>
    buildInitialAgentRunIds(normalizedAgentNames),
  );
  const [streamState, setStreamState] = useState<string>('waiting');
  const [errorText, setErrorText] = useState<string | null>(null);
  const [generalEvents, setGeneralEvents] = useState<MasGeneralEvents[]>([]);

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

  const handleSwarmEvent = useCallback((event: MessageEvent<string>) => {
    try {
      const raw = JSON.parse(event.data) as unknown;
      const parsed = parseEventStreamPayload(raw);
      if (!parsed) {
        setErrorText('Invalid stream payload');
        return;
      }

      setEntries((prev) => [...prev, parsed]);

      switch (parsed.event_type) {
        case 'swarm_started': {
          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Swarm Started',
            arch_type: 'MAS',
            description: 'Swarm has started.',
            created_at: parsed.created_at,
          });
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

            setAgentStatus((prev) => {
              return {
                ...prev,
                [agentName] : "running"
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

            setAgentStatus((prev) => {
              return {
                ...prev,
                [agentName] : "executed"
              }
            })
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

            setActiveHandoffEdges((prev) => ({
              ...prev,
              [edgeKey]: 'active',
            }));

            setAgentStatus((prev) => {
              return {
                ...prev,
                [fromAgent] : "executed",
                [toAgent] : "running"
              }
            })

            handoffTimeoutsRef.current[edgeKey] = window.setTimeout(() => {
              setActiveHandoffEdges((prev) => ({
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
  }, []);

  const handleDone = useCallback((event: MessageEvent<string>) => {
    void event;
    setStreamState('done');
    sourceRef.current?.close();
  }, []);

  const filteredEntries = useMemo(() => {
    if (activeAgentName === 'general') return entries;
    return entries.filter((entry) => entry.agent_name === activeAgentName);
  }, [activeAgentName, entries]);

  useEffect(() => {
    sourceRef.current?.close();

    if (!eventsStreamUrl) {
      setEntries([]);
      setGeneralEvents([]);
      setStreamState('waiting');
      setErrorText(null);
      for (const timeoutId of Object.values(handoffTimeoutsRef.current)) {
        window.clearTimeout(timeoutId);
      }
      handoffTimeoutsRef.current = {};
      return;
    }

    setEntries([]);
    setGeneralEvents([]);
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
        {activeAgentName === 'general' ? (
          <div className="flex h-full min-h-0 w-full flex-col bg-white">
            <div className="flex w-full shrink-0 flex-col gap-3 border-b border-slate-200 px-5 py-4">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="space-y-1">
                  <p className="text-xl font-semibold text-slate-900">General Traces</p>
                  <p className="text-xs font-semibold text-slate-600">
                    Run ID : <span className="font-mono text-slate-700">{swarm_run_id}</span>
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
                  Agents: {normalizedAgentNames.length}
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
        ) : null}
      </div>
    </div>
  );
}
