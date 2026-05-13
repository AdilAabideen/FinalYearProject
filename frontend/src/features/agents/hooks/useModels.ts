// Manages use models behavior.
import { useEffect, useState } from 'react';
import { modelService } from '../../../services/modelService';
import type { ModelSpec } from '../../../types/models';

export type ModelsStatus = 'loading' | 'error' | 'success';

// Manages models.
export function useModels() {
  const [models, setModels] = useState<ModelSpec[]>([]);
  const [status, setStatus] = useState<ModelsStatus>('loading');
  const [selectedModelId, setSelectedModelId] = useState<string>('');

// Manages effect.
  useEffect(() => {
    const ac = new AbortController();

// Loads models.
    async function loadModels() {
      setStatus('loading');
      try {
        const items = await modelService.listModels(ac.signal);
        if (ac.signal.aborted) return;
        setModels(items);
        setStatus('success');
// Sets selected model ID.
        setSelectedModelId((prev) => prev || items[0]?.id || '');
      } catch {
        if (ac.signal.aborted) return;
        setStatus('error');
        setModels([]);
      }
    }

    loadModels();
// Manages effect.
    return () => ac.abort();
  }, []);

  return { models, status, selectedModelId, setSelectedModelId };
}
