import { API_BASE_URL } from '../config/env';
import type { SwarmExecutionStartResponse, SwarmExecutionStartResponseDto, SwarmRunMetricsReadDto } from '../types/masRuns';

export type MasRunService = {
    startMasRun: (
        workflow_id: string,
        payload: Record<string, unknown>,
        signal?: AbortSignal,
    ) => Promise<SwarmExecutionStartResponse>;
    getMasRunMetrics: (
        swarmRunId: string,
        signal?: AbortSignal,
    ) => Promise<any>;

}

export const masRunService: MasRunService = {

    async startMasRun(workflow_id, payload, signal) {

        const response = await fetch(`${API_BASE_URL}/api/mas/${workflow_id}/runs`, {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                input: payload
            }),
            signal
        })

        if (!response.ok) {
            const message = await response.text();
            throw new Error(message || 'Failed to start agent run');
        }

        const data = (await response.json()) as SwarmExecutionStartResponseDto

        return {
            swarmRunId: data.swarm_run_id,
            status: data.status,
            runUrl: data.run_url,
            summaryUrl: data.summary_url,
            eventsUrl: data.events_url,
            eventsStreamUrl: data.events_stream_url,
            agentsUrl: data.agents_url,
            handoffsUrl: data.handoffs_url,
            gateEvaluationsUrl: data.gate_evaluations_url,
            finalOutputUrl: data.final_output_url
        }
    },

    async getMasRunMetrics(swarmRunId, signal) {

        const response = await fetch(`${API_BASE_URL}/api/swarm-runs/${encodeURIComponent(swarmRunId)}/metrics`, {
            method: 'GET',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
            },
            signal
        })


        if (!response.ok) {
            const message = await response.text();
            throw new Error(message || 'Failed to start agent run');
        }

        const data = (await response.json()) as SwarmRunMetricsReadDto

        return {
            swarmRunId: data.swarm_run_id,
            status: data.status,
            durationMs: data.duration_ms,
            agentRunCount: data.agent_run_count,
            handoffCount: data.handoff_count,
            gateEvaluationCount: data.gate_evaluation_count,
            completedAgentCount: data.completed_agent_count,
            failedAgentCount: data.failed_agent_count,
            inputTokensTotal: data.input_tokens_total,
            outputTokensTotal: data.output_tokens_total,
            tokensTotal: data.tokens_total,
            llmCallCountTotal: data.llm_call_count_total,
            toolCallCountTotal: data.tool_call_count_total,
            toolErrorCountTotal: data.tool_error_count_total,
            costUsdTotal: data.cost_usd_total,
            costUsdPerAgentRun: data.cost_usd_per_agent_run,
            agentFailureCount: data.agent_failure_count,
            reliabilityIssueCount: data.reliability_issue_count,
            reliabilityErrorCount: data.reliability_error_count,
            finalizationFailureCount: data.finalization_failure_count,
            createdAt: data.created_at,
            updatedAt: data.updated_at,
        };

    }


}