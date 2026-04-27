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