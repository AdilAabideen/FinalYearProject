// Manages use MAS agent metrics store behavior.
import { useCallback, useEffect, useRef, useState } from 'react';
import { agentRunService } from '../../../services/agentRunService';
import type { MetricsState } from '../utils/masTraces';

const IDLE_METRICS_STATE: MetricsState = { status: 'idle' };

// Manages MAS agent metrics store.
export function useMasAgentMetricsStore() {
  const metricsAbortRefs = useRef<Record<string, AbortController>>({});
  const [agentMetricsStates, setAgentMetricsStates] = useState<Record<string, MetricsState>>({});

// Manages effect.
  useEffect(() => {
// Manages effect.
    return () => {
      for (const controller of Object.values(metricsAbortRefs.current)) {
        controller.abort();
      }
      metricsAbortRefs.current = {};
    };
  }, []);

// Manages callback.
  const getAgentMetrics = useCallback(async (agentName: string, runId: string) => {
    metricsAbortRefs.current[agentName]?.abort();

    const ac = new AbortController();
    metricsAbortRefs.current[agentName] = ac;

// Sets agent metrics states.
    setAgentMetricsStates((prev) => ({
      ...prev,
      [agentName]: { status: 'loading' },
    }));

    try {
      const metrics = await agentRunService.getAgentRunMetrics(runId, ac.signal);
      if (ac.signal.aborted) return;

// Sets agent metrics states.
      setAgentMetricsStates((prev) => ({
        ...prev,
        [agentName]: { status: 'ready', metrics },
      }));
    } catch (error) {
      if (ac.signal.aborted) return;
      console.error(error);
// Sets agent metrics states.
      setAgentMetricsStates((prev) => ({
        ...prev,
        [agentName]: {
          status: 'error',
          error: error instanceof Error ? error.message : 'Failed to load metrics',
        },
      }));
    } finally {
      if (metricsAbortRefs.current[agentName] === ac) {
        delete metricsAbortRefs.current[agentName];
      }
    }
  }, []);

// Manages callback.
  const resetAgentMetricsStates = useCallback(() => {
    for (const controller of Object.values(metricsAbortRefs.current)) {
      controller.abort();
    }
    metricsAbortRefs.current = {};
    setAgentMetricsStates({});
  }, []);

  return {
    agentMetricsStates,
    getAgentMetrics,
    resetAgentMetricsStates,
    idleMetricsState: IDLE_METRICS_STATE,
  };
}
