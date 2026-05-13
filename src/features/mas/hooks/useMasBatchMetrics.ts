// Manages use MAS batch metrics behavior.
import { useCallback, useEffect, useRef, useState } from 'react';
import type { MasTestRunMetrics } from '../../../types/masTests';
import { masTestService } from '../../../services/masTestService';

export type MasRunMetricsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: MasTestRunMetrics };

// Manages MAS batch metrics.
export function useMasBatchMetrics() {
  const [masRunMetricsState, setMasRunMetricsState] = useState<MasRunMetricsState>({ status: 'idle' });
  const batchMetricsAbortRef = useRef<AbortController | null>(null);

// Manages callback.
  const fetchMasRunMetrics = useCallback(async (runId: string) => {
    batchMetricsAbortRef.current?.abort();
    const ac = new AbortController();
    batchMetricsAbortRef.current = ac;
    setMasRunMetricsState({ status: 'loading' });

    try {
      const data = await masTestService.getRunMetrics(runId, ac.signal);
      if (ac.signal.aborted) return;
      setMasRunMetricsState({ status: 'ready', data });
    } catch (error) {
      if (ac.signal.aborted) return;
      setMasRunMetricsState({
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to load MAS test run metrics',
      });
    } finally {
      if (batchMetricsAbortRef.current === ac) {
        batchMetricsAbortRef.current = null;
      }
    }
  }, []);

// Manages callback.
  const resetMasRunMetrics = useCallback(() => {
    batchMetricsAbortRef.current?.abort();
    batchMetricsAbortRef.current = null;
    setMasRunMetricsState({ status: 'idle' });
  }, []);

// Manages effect.
  useEffect(() => {
// Manages effect.
    return () => {
      batchMetricsAbortRef.current?.abort();
      batchMetricsAbortRef.current = null;
    };
  }, []);

  return {
    masRunMetricsState,
    masRunMetrics: masRunMetricsState.status === 'ready' ? masRunMetricsState.data : null,
    fetchMasRunMetrics,
    resetMasRunMetrics,
  };
}
