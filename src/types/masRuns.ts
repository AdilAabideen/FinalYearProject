
type SwarmRunStatus = string;

export type SwarmExecutionStartResponseDto = {
    swarm_run_id: string;
    workflow_id: string;
    workflow_version: string | null;
    input_schema_name: string;
    status: SwarmRunStatus;
    run_url: string;
    summary_url: string;
    events_url: string;
    events_stream_url: string;
    agents_url: string;
    handoffs_url: string;
    gate_evaluations_url: string;
    final_output_url: string;
};

export type SwarmExecutionStartResponse = {
    swarmRunId: string;
    status: SwarmRunStatus;
    runUrl: string;
    summaryUrl: string;
    eventsUrl: string;
    eventsStreamUrl: string;
    agentsUrl: string;
    handoffsUrl: string;
    gateEvaluationsUrl: string;
    finalOutputUrl: string;
};

export type SwarmEventType =
| 'swarm_started'
| 'swarm_failed'
| 'agent_started'
| 'handoff_created'
| 'agent_completed'
| 'gate_evaluated'
| 'final_output_created'
| 'swarm_completed';

export type SwarmEventStatus =
| 'running'
| 'created'
| 'succeeded'
| 'blocked'
| 'ready'
| 'completed';

export type EventStreamPayload = {
id: number;
swarm_run_id: string;
seq: number;
event_type: SwarmEventType;
workflow_id: string;
agent_run_id: string | null;
agent_name: string | null;
handoff_id: string | null;
gate_evaluation_id: string | null;
final_output_id: string | null;
status: SwarmEventStatus | string;
payload_json: Record<string, unknown> | null;
payload_text: string | null;
created_at: string;
};
