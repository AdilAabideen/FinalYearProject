export type MasTestCaseReadDto = {
    id: string;
    workflow_id: string;
    name: string;
    enabled: boolean;
    input_json: Record<string, unknown>;
    expected_json: Record<string, unknown>;
    created_at: string;
    updated_at: string;
};

export type MasTestCaseRead = {
    id: string;
    workflowId: string;
    name: string;
    enabled: boolean;
    inputJson: Record<string, unknown>;
    expectedJson: Record<string, unknown>;
    createdAt: string;
    updatedAt: string;
};

export type MasTestRunResultsRunDto = {
    id: string;
    workflow_id: string;
    name: string | null;
    status: string;
    selected_case_ids_json: string[];
    metrics_json: Record<string, unknown> | null;
    started_at: string | null;
    finished_at: string | null;
    created_at: string;
    updated_at: string;
};

export type MasTestRunResultsSummaryDto = {
    total_runs?: number;
    runs_with_swarm_run?: number;
    successful_runs?: number;
    failed_runs?: number;
    success_rate?: number | null;
    execution_failed_count?: number;
    missing_final_output_count?: number;
    duration_ms_total?: number;
    duration_ms_avg?: number | null;
};

export type MasTestRunResultsCaseDto = {
    test_case_id: string;
    test_case_name: string;
    swarm_run_id: string | null;
    status: string;
    passed: boolean | null;
    score: number | null;
    failure_reason: string | null;
    swarm_status: string | null;
    duration_ms: number | null;
};


export type MasTestRunResultsDto = {
    run: MasTestRunResultsRunDto;
    summary: MasTestRunResultsSummaryDto | null;
    cases: MasTestRunResultsCaseDto[] | null;
};


export type MasTestRunResults = {
    run: MasTestRunResultsRun;
    summary: MasTestRunResultsSummary;
    cases: MasTestRunResultsCase[];
};

export type MasTestRunResultsRun = {
    id: string;
    workflowId: string;
    name: string | null;
    status: string;
    selectedCaseIds: string[];
    metricsJson: Record<string, unknown> | null;
    startedAt: string | null;
    finishedAt: string | null;
    createdAt: string;
    updatedAt: string;
};

export type MasTestRunResultsSummary = {
    totalRuns: number;
    runsWithSwarmRun: number;
    successfulRuns: number;
    failedRuns: number;
    successRate: number | null;
    executionFailedCount: number;
    missingFinalOutputCount: number;
    durationMsTotal: number;
    durationMsAvg: number | null;
};

export type MasTestRunResultsCase = {
    testCaseId: string;
    testCaseName: string;
    swarmRunId: string | null;
    status: string;
    passed: boolean | null;
    score: number | null;
    failureReason: string | null;
    swarmStatus: string | null;
    durationMs: number | null;
};


export type MasTestRunMetricsRunDto = {
    id: string;
    workflow_id: string;
    name: string | null;
    status: string;
    selected_case_ids_json: string[];
    metrics_json: Record<string, unknown> | null;
    started_at: string | null;
    finished_at: string | null;
    created_at: string;
    updated_at: string;
};

export type MasTestRunMetricsSummaryDto = {
    total_cases?: number;
    cases_with_swarm_run?: number;
    cases_with_metrics?: number;
    duration_ms_total?: number;
    duration_ms_avg?: number | null;
    agent_run_count_total?: number;
    agent_run_count_avg?: number | null;
    handoff_count_total?: number;
    handoff_count_avg?: number | null;
    gate_evaluation_count_total?: number;
    gate_evaluation_count_avg?: number | null;
    input_tokens_total?: number;
    input_tokens_avg?: number | null;
    output_tokens_total?: number;
    output_tokens_avg?: number | null;
    tokens_total?: number;
    tokens_avg?: number | null;
    llm_call_count_total?: number;
    llm_call_count_avg?: number | null;
    tool_call_count_total?: number;
    tool_call_count_avg?: number | null;
    tool_error_count_total?: number;
    tool_error_count_avg?: number | null;
    cost_usd_total?: number | null;
    cost_usd_avg?: number | null;
    reliability_issue_count_total?: number;
    reliability_issue_count_avg?: number | null;
    reliability_error_count_total?: number;
    reliability_error_count_avg?: number | null;
    finalization_failure_count_total?: number;
    finalization_failure_count_avg?: number | null;
};

export type MasTestRunMetricsCaseDto = {
    test_case_id: string;
    test_case_name: string;
    swarm_run_id: string | null;
    swarm_status: string | null;
    duration_ms: number | null;
    agent_run_count: number | null;
    handoff_count: number | null;
    gate_evaluation_count: number | null;
    input_tokens_total: number | null;
    output_tokens_total: number | null;
    tokens_total: number | null;
    llm_call_count_total: number | null;
    tool_call_count_total: number | null;
    tool_error_count_total: number | null;
    cost_usd_total: number | null;
    cost_usd_per_agent_run: number | null;
    reliability_issue_count: number | null;
    reliability_error_count: number | null;
    finalization_failure_count: number | null;
};

export type MasTestRunMetricsDto = {
    run: MasTestRunMetricsRunDto;
    summary: MasTestRunMetricsSummaryDto | null;
    cases: MasTestRunMetricsCaseDto[] | null;
};

export type MasTestRunMetricsRun = {
    id: string;
    workflowId: string;
    name: string | null;
    status: string;
    selectedCaseIds: string[];
    metricsJson: Record<string, unknown> | null;
    startedAt: string | null;
    finishedAt: string | null;
    createdAt: string;
    updatedAt: string;
};

export type MasTestRunMetricsSummary = {
    totalCases: number;
    casesWithSwarmRun: number;
    casesWithMetrics: number;
    durationMsTotal: number;
    durationMsAvg: number | null;
    agentRunCountTotal: number;
    agentRunCountAvg: number | null;
    handoffCountTotal: number;
    handoffCountAvg: number | null;
    gateEvaluationCountTotal: number;
    gateEvaluationCountAvg: number | null;
    inputTokensTotal: number;
    inputTokensAvg: number | null;
    outputTokensTotal: number;
    outputTokensAvg: number | null;
    tokensTotal: number;
    tokensAvg: number | null;
    llmCallCountTotal: number;
    llmCallCountAvg: number | null;
    toolCallCountTotal: number;
    toolCallCountAvg: number | null;
    toolErrorCountTotal: number;
    toolErrorCountAvg: number | null;
    costUsdTotal: number | null;
    costUsdAvg: number | null;
    reliabilityIssueCountTotal: number;
    reliabilityIssueCountAvg: number | null;
    reliabilityErrorCountTotal: number;
    reliabilityErrorCountAvg: number | null;
    finalizationFailureCountTotal: number;
    finalizationFailureCountAvg: number | null;
};

export type MasTestRunMetricsCase = {
    testCaseId: string;
    testCaseName: string;
    swarmRunId: string | null;
    swarmStatus: string | null;
    durationMs: number | null;
    agentRunCount: number | null;
    handoffCount: number | null;
    gateEvaluationCount: number | null;
    inputTokensTotal: number | null;
    outputTokensTotal: number | null;
    tokensTotal: number | null;
    llmCallCountTotal: number | null;
    toolCallCountTotal: number | null;
    toolErrorCountTotal: number | null;
    costUsdTotal: number | null;
    costUsdPerAgentRun: number | null;
    reliabilityIssueCount: number | null;
    reliabilityErrorCount: number | null;
    finalizationFailureCount: number | null;
};

export type MasTestRunMetrics = {
    run: MasTestRunMetricsRun;
    summary: MasTestRunMetricsSummary;
    cases: MasTestRunMetricsCase[];
};
