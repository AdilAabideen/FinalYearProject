import { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE_URL } from '../../../config/env';
import { masRunService } from '../../../services/masRunService';
import type { SwarmRunMetricsRead } from '../../../types/masRuns';

export function useMasCaseCompletionData() {
  const [testCaseOutputs, setTestCaseOutputs] = useState<Record<string, Record<string, unknown> | null>>({});
  const [testCaseMetrics, setTestCaseMetrics] = useState<Record<string, SwarmRunMetricsRead | null>>({});
  const doneAbortRefs = useRef<Record<string, AbortController>>({});

  const handleMasDone = useCallback(async (testCaseId: string, swarmRunId: string) => {
    const outputResponse = await fetch(
      `${API_BASE_URL}/api/swarm-runs/${encodeURIComponent(swarmRunId)}/final-output`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      },
    );

    if (!outputResponse.ok) {
      const message = await outputResponse.text();
      throw new Error(message || 'Failed to fetch MAS final output');
    }

    const output = (await outputResponse.json()) as Record<string, unknown>;
    setTestCaseOutputs((prev) => ({
      ...prev,
      [testCaseId]: output,
    }));

    doneAbortRefs.current[testCaseId]?.abort();
    const ac = new AbortController();
    doneAbortRefs.current[testCaseId] = ac;

    try {
      const metrics = await masRunService.getMasRunMetrics(swarmRunId, ac.signal);
      if (ac.signal.aborted) return;
      setTestCaseMetrics((prev) => ({
        ...prev,
        [testCaseId]: metrics,
      }));
    } finally {
      if (doneAbortRefs.current[testCaseId] === ac) {
        delete doneAbortRefs.current[testCaseId];
      }
    }
  }, []);

  const resetCaseCompletionData = useCallback(() => {
    for (const controller of Object.values(doneAbortRefs.current)) {
      controller.abort();
    }
    doneAbortRefs.current = {};
    setTestCaseOutputs({});
    setTestCaseMetrics({});
  }, []);

  useEffect(() => {
    return () => {
      for (const controller of Object.values(doneAbortRefs.current)) {
        controller.abort();
      }
      doneAbortRefs.current = {};
    };
  }, []);

  return {
    testCaseOutputs,
    testCaseMetrics,
    handleMasDone,
    resetCaseCompletionData,
  };
}
