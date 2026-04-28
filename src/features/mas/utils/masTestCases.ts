import { isRecord } from '../../agents/utils/runResult';

export type TestCaseTabKey = 'test_case' | 'traces' | 'output' | 'metrics' | 'diff';
export type MasTestTabKey = 'test' | 'output' | 'metrics';

export type TestCaseTraceRun = {
  swarmRunId: string;
  eventsStreamUrl: string;
};

export type TestCaseRunStatus = 'idle' | 'running' | 'passed' | 'failed';

export type TestCaseDiffState = {
  status: 'idle' | 'ready' | 'error';
  diff?: Record<string, unknown> | null;
  passed?: boolean | null;
  score?: number | null;
  swarmStatus?: string | null;
  error?: string;
};

export function buildSwarmEventsStreamUrl(apiBaseUrl: string, swarmRunId: string) {
  return `${apiBaseUrl}/api/swarm-runs/${encodeURIComponent(swarmRunId)}/events/stream`;
}

export function getExpectedAcuityFromDiff(diffState?: TestCaseDiffState) {
  const selectedDiffRecord =
    diffState?.status === 'ready' && isRecord(diffState.diff)
      ? diffState.diff
      : null;
  const expectedAnswerRecord =
    selectedDiffRecord && isRecord(selectedDiffRecord.expected_answer)
      ? selectedDiffRecord.expected_answer
      : null;

  return expectedAnswerRecord &&
    (typeof expectedAnswerRecord.acuity === 'string' || typeof expectedAnswerRecord.acuity === 'number')
    ? String(expectedAnswerRecord.acuity)
    : '—';
}

export function getActualFinalEsiLevelFromDiff(diffState?: TestCaseDiffState) {
  const selectedDiffRecord =
    diffState?.status === 'ready' && isRecord(diffState.diff)
      ? diffState.diff
      : null;
  const actualAnswerRecord =
    selectedDiffRecord && isRecord(selectedDiffRecord.actual_answer)
      ? selectedDiffRecord.actual_answer
      : null;

  return actualAnswerRecord &&
    (typeof actualAnswerRecord.final_esi_level === 'string' ||
      typeof actualAnswerRecord.final_esi_level === 'number')
    ? String(actualAnswerRecord.final_esi_level)
    : '—';
}

export function summarizeRunStatuses(
  testCaseRunStatuses: Record<string, TestCaseRunStatus>,
  selectedCount: number,
) {
  const ranCount = Object.values(testCaseRunStatuses).filter(
    (status) => status === 'passed' || status === 'failed',
  ).length;
  const passedCount = Object.values(testCaseRunStatuses).filter((status) => status === 'passed').length;
  const failedCount = Object.values(testCaseRunStatuses).filter((status) => status === 'failed').length;

  return {
    ranCount,
    passedCount,
    failedCount,
    toRunCount: selectedCount - ranCount,
  };
}
