// Manages use MAS batch results behavior.
import { useCallback, useEffect, useRef, useState } from 'react';
import type { MasTestRunResults } from '../../../types/masTests';
import { masTestService } from '../../../services/masTestService';

export type MasRunResultsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: MasTestRunResults };

// Manages MAS batch results.
export function useMasBatchResults() {
  const [masRunResultsState, setMasRunResultsState] = useState<MasRunResultsState>({ status: 'idle' });
  const resultsAbortRef = useRef<AbortController | null>(null);

// Manages callback.
  const fetchMasRunResults = useCallback(async (runId: string) => {
    resultsAbortRef.current?.abort();
    const ac = new AbortController();
    resultsAbortRef.current = ac;
    setMasRunResultsState({ status: 'loading' });

    try {
      const data = await masTestService.getRunResults(runId, ac.signal);
      if (ac.signal.aborted) return;
      setMasRunResultsState({ status: 'ready', data });
    } catch (error) {
      if (ac.signal.aborted) return;
      setMasRunResultsState({
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to load MAS test run results',
      });
    } finally {
      if (resultsAbortRef.current === ac) {
        resultsAbortRef.current = null;
      }
    }
  }, []);

// Manages callback.
  const resetMasRunResults = useCallback(() => {
    resultsAbortRef.current?.abort();
    resultsAbortRef.current = null;
    setMasRunResultsState({ status: 'idle' });
  }, []);

// Manages effect.
  useEffect(() => {
// Manages effect.
    return () => {
      resultsAbortRef.current?.abort();
      resultsAbortRef.current = null;
    };
  }, []);

  return {
    masRunResultsState,
    masRunResults: masRunResultsState.status === 'ready' ? masRunResultsState.data : null,
    fetchMasRunResults,
    resetMasRunResults,
  };
}
