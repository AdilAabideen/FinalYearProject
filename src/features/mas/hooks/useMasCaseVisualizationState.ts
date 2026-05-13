// Manages use MAS case visualization state behavior.
import { useCallback, useMemo, useState } from 'react';
import type {
  ActiveHandoffEdges,
  AgentRunningStatus,
  BoundaryEdgeHighlights,
} from '../components/MasDetailSplitView';
import { buildInitialAgentStatus } from '../utils/agentState';

// Manages MAS case visualization state.
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
// Manages memo.
    () =>
      selectedTestCaseId
        ? testCaseAgentStatuses[selectedTestCaseId] ?? buildInitialAgentStatus(participatingAgents)
        : buildInitialAgentStatus(participatingAgents),
    [participatingAgents, selectedTestCaseId, testCaseAgentStatuses],
  );
  const selectedHandoffEdges = useMemo(
// Manages memo.
    () => (selectedTestCaseId ? testCaseHandoffEdges[selectedTestCaseId] ?? {} : {}),
    [selectedTestCaseId, testCaseHandoffEdges],
  );
  const selectedBoundaryHighlights = useMemo(
// Manages memo.
    () =>
      selectedTestCaseId
        ? testCaseBoundaryHighlights[selectedTestCaseId] ?? { start: 'idle', end: 'idle' }
        : ({ start: 'idle', end: 'idle' } as const),
    [selectedTestCaseId, testCaseBoundaryHighlights],
  );

// Manages callback.
  const initializeCaseVisualState = useCallback((testCaseId: string) => {
// Sets test case agent statuses.
    setTestCaseAgentStatuses((prev) => ({
      ...prev,
      [testCaseId]: buildInitialAgentStatus(participatingAgents),
    }));
// Sets test case handoff edges.
    setTestCaseHandoffEdges((prev) => ({
      ...prev,
      [testCaseId]: {},
    }));
// Sets test case boundary highlights.
    setTestCaseBoundaryHighlights((prev) => ({
      ...prev,
      [testCaseId]: { start: 'idle', end: 'idle' },
    }));
  }, [participatingAgents]);

// Manages callback.
  const resetVisualizationState = useCallback(() => {
    setTestCaseAgentStatuses({});
    setTestCaseHandoffEdges({});
    setTestCaseBoundaryHighlights({});
  }, []);

  const updateSelectedAgentStatus = useCallback(
// Manages callback.
    (value: AgentRunningStatus | ((prev: AgentRunningStatus) => AgentRunningStatus)) => {
      if (!selectedTestCaseId) return;

// Sets test case agent statuses.
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
// Manages callback.
    (value: ActiveHandoffEdges | ((prev: ActiveHandoffEdges) => ActiveHandoffEdges)) => {
      if (!selectedTestCaseId) return;

// Sets test case handoff edges.
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
// Manages callback.
    (
      value:
        | BoundaryEdgeHighlights
        | ((prev: BoundaryEdgeHighlights) => BoundaryEdgeHighlights),
    ) => {
      if (!selectedTestCaseId) return;

// Sets test case boundary highlights.
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
