import { useEffect, useState } from 'react';
import { modelService } from '../../../services/modelService';
import type { ModelSpec } from '../../../types/models';

export type ModelsStatus = 'loading' | 'error' | 'success';

export function useModels() {
  const [models, setModels] = useState<ModelSpec[]>([]);
  const [status, setStatus] = useState<ModelsStatus>('loading');
  const [selectedModelId, setSelectedModelId] = useState<string>('');

  useEffect(() => {
    const ac = new AbortController();

    async function loadModels() {
      setStatus('loading');
      try {
        const items = await modelService.listModels(ac.signal);
        if (ac.signal.aborted) return;
        setModels(items);
        setStatus('success');
        setSelectedModelId((prev) => prev || items[0]?.id || '');
      } catch {
        if (ac.signal.aborted) return;
        setStatus('error');
        setModels([]);
      }
    }

    loadModels();
    return () => ac.abort();
  }, []);

  return { models, status, selectedModelId, setSelectedModelId };
}
