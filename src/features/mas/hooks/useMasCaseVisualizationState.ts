import { useCallback, useMemo, useState } from 'react';
import type {
  ActiveHandoffEdges,
  AgentRunningStatus,
  BoundaryEdgeHighlights,
} from '../components/MasDetailSplitView';
import { buildInitialAgentStatus } from '../utils/agentState';

export function useMasCaseVisualizationState(
  participatingAgents: string[],
  selectedTestCaseId: string | null,
) {
  const [testCaseAgentStatuses, setTestCaseAgentStatuses] = useState<Record<string, AgentRunningStatus>>({});
  const [testCaseHandoffEdges, setTestCaseHandoffEdges] = useState<Record<string, ActiveHandoffEdges>>({});
  const [testCaseBoundaryHighlights, setTestCaseBoundaryHighlights] = useState<
    Record<string, BoundaryEdgeHighlights>
  >({});

  const selectedAgentStatus = useMemo(
    () =>
      selectedTestCaseId
        ? testCaseAgentStatuses[selectedTestCaseId] ?? buildInitialAgentStatus(participatingAgents)
        : buildInitialAgentStatus(participatingAgents),
    [participatingAgents, selectedTestCaseId, testCaseAgentStatuses],
  );
  const selectedHandoffEdges = useMemo(
    () => (selectedTestCaseId ? testCaseHandoffEdges[selectedTestCaseId] ?? {} : {}),
    [selectedTestCaseId, testCaseHandoffEdges],
  );
  const selectedBoundaryHighlights = useMemo(
    () =>
      selectedTestCaseId
        ? testCaseBoundaryHighlights[selectedTestCaseId] ?? { start: 'idle', end: 'idle' }
        : ({ start: 'idle', end: 'idle' } as const),
    [selectedTestCaseId, testCaseBoundaryHighlights],
  );

  const initializeCaseVisualState = useCallback((testCaseId: string) => {
    setTestCaseAgentStatuses((prev) => ({
      ...prev,
      [testCaseId]: buildInitialAgentStatus(participatingAgents),
    }));
    setTestCaseHandoffEdges((prev) => ({
      ...prev,
      [testCaseId]: {},
    }));
    setTestCaseBoundaryHighlights((prev) => ({
      ...prev,
      [testCaseId]: { start: 'idle', end: 'idle' },
    }));
  }, [participatingAgents]);

  const resetVisualizationState = useCallback(() => {
    setTestCaseAgentStatuses({});
    setTestCaseHandoffEdges({});
    setTestCaseBoundaryHighlights({});
  }, []);

  const updateSelectedAgentStatus = useCallback(
    (value: AgentRunningStatus | ((prev: AgentRunningStatus) => AgentRunningStatus)) => {
      if (!selectedTestCaseId) return;

      setTestCaseAgentStatuses((prev) => {
        const current = prev[selectedTestCaseId] ?? buildInitialAgentStatus(participatingAgents);
        const nextValue = typeof value === 'function' ? value(current) : value;
        return {
          ...prev,
          [selectedTestCaseId]: nextValue,
        };
      });
    },
    [participatingAgents, selectedTestCaseId],
  );

  const updateSelectedHandoffEdges = useCallback(
    (value: ActiveHandoffEdges | ((prev: ActiveHandoffEdges) => ActiveHandoffEdges)) => {
      if (!selectedTestCaseId) return;

      setTestCaseHandoffEdges((prev) => {
        const current = prev[selectedTestCaseId] ?? {};
        const nextValue = typeof value === 'function' ? value(current) : value;
        return {
          ...prev,
          [selectedTestCaseId]: nextValue,
        };
      });
    },
    [selectedTestCaseId],
  );

  const updateSelectedBoundaryHighlights = useCallback(
    (
      value:
        | BoundaryEdgeHighlights
        | ((prev: BoundaryEdgeHighlights) => BoundaryEdgeHighlights),
    ) => {
      if (!selectedTestCaseId) return;

      setTestCaseBoundaryHighlights((prev) => {
        const current = prev[selectedTestCaseId] ?? { start: 'idle', end: 'idle' };
        const nextValue = typeof value === 'function' ? value(current) : value;
        return {
          ...prev,
          [selectedTestCaseId]: nextValue,
        };
      });
    },
    [selectedTestCaseId],
  );

  return {
    selectedAgentStatus,
    selectedHandoffEdges,
    selectedBoundaryHighlights,
    updateSelectedAgentStatus,
    updateSelectedHandoffEdges,
    updateSelectedBoundaryHighlights,
    initializeCaseVisualState,
    resetVisualizationState,
  };
}
