import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { EventStreamPayload, SwarmEventType } from '../../../types/masRuns';

type MasTracesTabProps = {
  agentNames: string[];
  eventsStreamUrl: string;
  swarm_run_id: string;
};

type MasEventTypes = "Swarm Started" | "Swarm Ended" | 'Agent Execution Started' | "Agent Execution Finished" | "Swarm Error" | 'Handoff' | 'Gate Evaluated'
type ArchType = "MAS" | "Agent"

type MasGeneralEvents = {
  event_type: MasEventTypes;
  arch_type: ArchType;
  description: string;
}

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
  setGeneralEvents((prev) => [
    ...prev,
    event,
  ]);
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

export default function MasTracesTab({ agentNames, eventsStreamUrl, swarm_run_id }: MasTracesTabProps) {
  const normalizedAgentNames = useMemo(
    () => agentNames.filter((name, index, arr) => arr.indexOf(name) === index),
    [agentNames],
  );

  const [activeAgentName, setActiveAgentName] = useState<string>('general');

  const sourceRef = useRef<EventSource | null>(null);
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
          });
          break;
        }

        case 'swarm_completed': {
          setStreamState('done');
          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Swarm Ended',
            arch_type: 'MAS',
            description: 'Swarm completed successfully.',
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
          });

          if (agentName) {
            setAgentRunIds((prev) => ({
              ...prev,
              [agentName]: agentRunId,
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
          });

          if (agentName) {
            setAgentRunIds((prev) => ({
              ...prev,
              [agentName]: agentRunId,
            }));
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
          });
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

          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Gate Evaluated',
            arch_type: 'MAS',
            description: `Gate evaluated. Missing sources: ${missingSources.join(', ')}.
        Satisfied sources: ${satisfiedSources.join(', ')}.`,
          });
          break;
        }
        case 'final_output_created': {
          appendGeneralEvent(setGeneralEvents, {
            event_type: 'Gate Evaluated',
            arch_type: 'MAS',
            description: "Mas Output finished"
          })
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
          <div className="flex h-full min-h-0 w-full flex-col items-start justify-start">
            <div className="flex w-full shrink-0 flex-col items-start gap-1 border-b border-slate-200 p-2">
              <p className="text-lg font-medium text-slate-900">General Traces</p>
              <p className="text-xs font-semibold text-slate-600">Run ID : <span className="font-mono text-slate-700">{swarm_run_id}</span></p>
            </div>
            <div className="flex-1 min-h-0 w-full overflow-y-auto p-3 pt-3">
              <div className="flex w-full flex-col items-start justify-start gap-6 p-2 pt-0 pb-0 mb-40">
              {generalEvents.map((event, index) => (
                <div key={index} className="flex flex-col items-start gap-1">
                  <p className="text-xs font-bold capitalize text-PrimaryBlue">SWARM EVENT</p>
                  <p className="text-md text-slate-900 font-medium">{event.event_type}</p>
                  <p className="text-sm text-slate-700">{event.description}</p>
                </div>
              ))}
              </div>
            </div>

          </div>
        ) : null}
      </div>
    </div>
  );
}
