
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

export type SwarmRunMetricsReadDto = {
    swarm_run_id: string;
    status: string;
    duration_ms: number | null;
    agent_run_count: number;
    handoff_count: number;
    gate_evaluation_count: number;
    completed_agent_count: number;
    failed_agent_count: number;
    input_tokens_total: number;
    output_tokens_total: number;
    tokens_total: number;
    llm_call_count_total: number;
    tool_call_count_total: number;
    tool_error_count_total: number;
    cost_usd_total: number | null;
    cost_usd_per_agent_run: number | null;
    agent_failure_count: number;
    reliability_issue_count: number;
    reliability_error_count: number;
    finalization_failure_count: number;
    created_at: string;
    updated_at: string;
};

export type SwarmRunMetricsRead = {
    swarmRunId: string;
    status: string;
    durationMs: number | null;
    agentRunCount: number;
    handoffCount: number;
    gateEvaluationCount: number;
    completedAgentCount: number;
    failedAgentCount: number;
    inputTokensTotal: number;
    outputTokensTotal: number;
    tokensTotal: number;
    llmCallCountTotal: number;
    toolCallCountTotal: number;
    toolErrorCountTotal: number;
    costUsdTotal: number | null;
    costUsdPerAgentRun: number | null;
    agentFailureCount: number;
    reliabilityIssueCount: number;
    reliabilityErrorCount: number;
    finalizationFailureCount: number;
    createdAt: string;
    updatedAt: string;
};