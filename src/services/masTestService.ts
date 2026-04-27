import { API_BASE_URL } from "../config/env";
import type { MasTestCaseRead, MasTestCaseReadDto } from "../types/masTests";

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
}

export const masTestService: MasTestService = {

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

        return data?.map((item) => ({
          id: item.id,
          workflowId: item.workflow_id,
          name: item.name,
          enabled: item.enabled,
          inputJson: item.input_json,
          expectedJson: item.expected_json,
          createdAt: item.created_at,
          updatedAt: item.updated_at,
        }));

    }
}
