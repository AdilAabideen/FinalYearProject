// Calls the MAS test service API.
import { API_BASE_URL } from "../config/env";
import type {
    MasTestCaseRead,
    MasTestCaseReadDto,
    MasTestRunMetrics,
    MasTestRunMetricsDto,
    MasTestRunResults,
    MasTestRunResultsDto,
} from "../types/masTests";

export type ListMasTestCasesParams = {
    workflow_id?: string;
    enabled?: boolean;
    limit?: number;
    offset?: number;
    order?: 'asc' | 'desc';
};

export type MasTestService = {
    listTestCases: (
        params: ListMasTestCasesParams,
        signal?: AbortSignal
    ) => Promise<MasTestCaseRead[]>;
    getRunResults: (
        runId: string,
        signal?: AbortSignal
    ) => Promise<MasTestRunResults>;
    getRunMetrics: (
        runId: string,
        signal?: AbortSignal
    ) => Promise<MasTestRunMetrics>;
}

export const masTestService: MasTestService = {

// Lists test cases.
    async listTestCases(params, signal) {
        const search = new URLSearchParams()
        if (!params.workflow_id) {
            throw new Error("Please Provide Workflow Id ")
        }
        if (params?.workflow_id) search.set('workflow_id', params.workflow_id);
        if (typeof params?.enabled === 'boolean') search.set('enabled', String(params.enabled));
        if (typeof params?.limit === 'number') search.set('limit', String(params.limit));
        if (typeof params?.offset === 'number') search.set('offset', String(params.offset));
        if (params?.order) search.set('order', params.order);

        const query = search.toString();
        const url = `${API_BASE_URL}/api/mas-tests/cases${query ? `?${query}` : ''}`;

        const response = await fetch(url, {
            method: 'GET',
            headers: { Accept: 'application/json' },
            signal,
        });

        if (!response.ok) {
            const message = await response.text();
            throw new Error(message || 'Failed to load test cases');
        }

        const data = (await response.json()) as MasTestCaseReadDto[];

// Maps logic.
        return data.map((item) => ({
            id: item.id,
            workflowId: item.workflow_id,
            name: item.name,
            enabled: item.enabled,
            inputJson: item.input_json,
            expectedJson: item.expected_json,
            createdAt: item.created_at,
            updatedAt: item.updated_at,
        }));

    },

// Gets run results.
    async getRunResults(runId, signal) {
        const url = `${API_BASE_URL}/api/mas-tests/runs/${encodeURIComponent(runId)}/results`;
        const response = await fetch(url, {
            method: 'GET',
            headers: { Accept: 'application/json' },
            signal,
        });

        if (!response.ok) {
            const message = await response.text();
            throw new Error(message || 'Failed to load MAS test run results');
        }

        const data = (await response.json()) as MasTestRunResultsDto;
        const summary = data.summary ?? {};
        const cases = Array.isArray(data.cases) ? data.cases : [];

        return {
            run: {
                id: data.run.id,
                workflowId: data.run.workflow_id,
                name: data.run.name ?? null,
                status: data.run.status,
                selectedCaseIds: data.run.selected_case_ids_json,
                metricsJson: data.run.metrics_json ?? null,
                startedAt: data.run.started_at ?? null,
                finishedAt: data.run.finished_at ?? null,
                createdAt: data.run.created_at,
                updatedAt: data.run.updated_at,
            },
            summary: {
                totalRuns: summary.total_runs ?? 0,
                runsWithSwarmRun: summary.runs_with_swarm_run ?? 0,
                successfulRuns: summary.successful_runs ?? 0,
                failedRuns: summary.failed_runs ?? 0,
                successRate: summary.success_rate ?? null,
                executionFailedCount: summary.execution_failed_count ?? 0,
                missingFinalOutputCount: summary.missing_final_output_count ?? 0,
                durationMsTotal: summary.duration_ms_total ?? 0,
                durationMsAvg: summary.duration_ms_avg ?? null,
            },
// Maps logic.
            cases: cases.map((item) => ({
                testCaseId: item.test_case_id,
                testCaseName: item.test_case_name,
                swarmRunId: item.swarm_run_id ?? null,
                status: item.status,
                passed: typeof item.passed === 'boolean' ? item.passed : null,
                score: typeof item.score === 'number' ? item.score : null,
                failureReason: item.failure_reason ?? null,
                swarmStatus: item.swarm_status ?? null,
                durationMs: typeof item.duration_ms === 'number' ? item.duration_ms : null,
            })),
        };
    },

// Gets run metrics.
    async getRunMetrics(runId, signal) {
        const url = `${API_BASE_URL}/api/mas-tests/runs/${encodeURIComponent(runId)}/metrics`;
        const response = await fetch(url, {
            method: 'GET',
            headers: { Accept: 'application/json' },
            signal,
        });

        if (!response.ok) {
            const message = await response.text();
            throw new Error(message || 'Failed to load MAS test run metrics');
        }

        const data = (await response.json()) as MasTestRunMetricsDto;
        const summary = data.summary ?? {};
        const cases = Array.isArray(data.cases) ? data.cases : [];

        return {
            run: {
                id: data.run.id,
                workflowId: data.run.workflow_id,
                name: data.run.name ?? null,
                status: data.run.status,
                selectedCaseIds: data.run.selected_case_ids_json,
                metricsJson: data.run.metrics_json ?? null,
                startedAt: data.run.started_at ?? null,
                finishedAt: data.run.finished_at ?? null,
                createdAt: data.run.created_at,
                updatedAt: data.run.updated_at,
            },
            summary: {
                totalCases: summary.total_cases ?? 0,
                casesWithSwarmRun: summary.cases_with_swarm_run ?? 0,
                casesWithMetrics: summary.cases_with_metrics ?? 0,
                durationMsTotal: summary.duration_ms_total ?? 0,
                durationMsAvg: summary.duration_ms_avg ?? null,
                agentRunCountTotal: summary.agent_run_count_total ?? 0,
                agentRunCountAvg: summary.agent_run_count_avg ?? null,
                handoffCountTotal: summary.handoff_count_total ?? 0,
                handoffCountAvg: summary.handoff_count_avg ?? null,
                gateEvaluationCountTotal: summary.gate_evaluation_count_total ?? 0,
                gateEvaluationCountAvg: summary.gate_evaluation_count_avg ?? null,
                inputTokensTotal: summary.input_tokens_total ?? 0,
                inputTokensAvg: summary.input_tokens_avg ?? null,
                outputTokensTotal: summary.output_tokens_total ?? 0,
                outputTokensAvg: summary.output_tokens_avg ?? null,
                tokensTotal: summary.tokens_total ?? 0,
                tokensAvg: summary.tokens_avg ?? null,
                llmCallCountTotal: summary.llm_call_count_total ?? 0,
                llmCallCountAvg: summary.llm_call_count_avg ?? null,
                toolCallCountTotal: summary.tool_call_count_total ?? 0,
                toolCallCountAvg: summary.tool_call_count_avg ?? null,
                toolErrorCountTotal: summary.tool_error_count_total ?? 0,
                toolErrorCountAvg: summary.tool_error_count_avg ?? null,
                costUsdTotal: summary.cost_usd_total ?? null,
                costUsdAvg: summary.cost_usd_avg ?? null,
                reliabilityIssueCountTotal: summary.reliability_issue_count_total ?? 0,
                reliabilityIssueCountAvg: summary.reliability_issue_count_avg ?? null,
                reliabilityErrorCountTotal: summary.reliability_error_count_total ?? 0,
                reliabilityErrorCountAvg: summary.reliability_error_count_avg ?? null,
                finalizationFailureCountTotal: summary.finalization_failure_count_total ?? 0,
                finalizationFailureCountAvg: summary.finalization_failure_count_avg ?? null,
            },
// Maps logic.
            cases: cases.map((item) => ({
                testCaseId: item.test_case_id,
                testCaseName: item.test_case_name,
                swarmRunId: item.swarm_run_id ?? null,
                swarmStatus: item.swarm_status ?? null,
                durationMs: item.duration_ms ?? null,
                agentRunCount: item.agent_run_count ?? null,
                handoffCount: item.handoff_count ?? null,
                gateEvaluationCount: item.gate_evaluation_count ?? null,
                inputTokensTotal: item.input_tokens_total ?? null,
                outputTokensTotal: item.output_tokens_total ?? null,
                tokensTotal: item.tokens_total ?? null,
                llmCallCountTotal: item.llm_call_count_total ?? null,
                toolCallCountTotal: item.tool_call_count_total ?? null,
                toolErrorCountTotal: item.tool_error_count_total ?? null,
                costUsdTotal: item.cost_usd_total ?? null,
                costUsdPerAgentRun: item.cost_usd_per_agent_run ?? null,
                reliabilityIssueCount: item.reliability_issue_count ?? null,
                reliabilityErrorCount: item.reliability_error_count ?? null,
                finalizationFailureCount: item.finalization_failure_count ?? null,
            })),
        };
    }
}
