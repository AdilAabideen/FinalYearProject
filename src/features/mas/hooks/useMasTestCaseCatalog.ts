import { useEffect, useRef, useState } from 'react';
import type { MasTestCaseRead } from '../../../types/masTests';
import { masTestService } from '../../../services/masTestService';

export function useMasTestCaseCatalog(workflowId: string | undefined) {
  const [testCases, setTestCases] = useState<MasTestCaseRead[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    async function loadTestCases(targetWorkflowId: string) {
      setLoading(true);

      try {
        const loadedTestCases = await masTestService.listTestCases({ workflow_id: targetWorkflowId }, ac.signal);
        if (ac.signal.aborted) return;
        setTestCases(loadedTestCases);
      } catch (error) {
        if (ac.signal.aborted) return;
        console.error('Error occurred', error);
        setTestCases([]);
      } finally {
        if (!ac.signal.aborted) {
          setLoading(false);
        }
      }
    }

    if (!workflowId) {
      setTestCases([]);
      setLoading(false);
      return () => {
        ac.abort();
      };
    }

    void loadTestCases(workflowId);

    return () => {
      ac.abort();
    };
  }, [workflowId]);

  return {
    testCases,
    loading,
  };
}
