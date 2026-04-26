import { API_BASE_URL } from '../config/env';
import type { SwarmExecutionStartResponse, SwarmExecutionStartResponseDto } from '../types/masRuns';

export type MasRunService = {
    startMasRun: (
        workflow_id: string,
        payload: Record<string, unknown>,
        signal?: AbortSignal,
    ) => Promise<SwarmExecutionStartResponse>
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
    }


}