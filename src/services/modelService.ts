// Calls the model service API.
import { API_BASE_URL } from '../config/env';
import type { ModelSpec, ModelSpecDto } from '../types/models';

export type ModelService = {
  listModels: (signal?: AbortSignal) => Promise<ModelSpec[]>;
};

// Fetches models.
async function fetchModels(path: string, signal?: AbortSignal) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  });
  return response;
}

export const modelService: ModelService = {
// Lists models.
  async listModels(signal) {
    let response = await fetchModels('/api/models', signal);

    if (!response.ok) {
      // Backwards compat with older route naming.
      response = await fetchModels('/api/model', signal);
    }

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || 'Failed to load models');
    }

    const data = (await response.json()) as ModelSpecDto[];

// Maps logic.
    return data.map((model) => ({
      id: model.id,
      provider: model.provider,
      description: model.description ?? null,
    }));
  },
};

