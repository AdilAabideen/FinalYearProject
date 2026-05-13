// Manages use MAS test run stream behavior.
import { useCallback, useEffect, useRef, useState } from 'react';
import { extractCaseId, extractDiff, extractPassed } from '../../agents/utils/testRunStream';
import { asString, isRecord } from '../../agents/utils/runResult';
import { API_BASE_URL } from '../../../config/env';
import { extractMasTestRunId, extractSwarmRunId } from '../utils/streamParsers';
import type { TestCaseDiffState, TestCaseRunStatus, TestCaseTraceRun } from '../utils/masTestCases';
import { buildSwarmEventsStreamUrl } from '../utils/masTestCases';

type UseMasTestRunStreamArgs = {
  workflowId: string;
  selectedTestCaseIds: string[];
  model_id? : string;
  onStartReset: () => void;
  onCaseBoundToSwarmRun: (testCaseId: string, swarmRunId: string) => void;
  onRunDone: (runId: string) => void;
};

// Manages MAS test run stream.
export function useMasTestRunStream({
  workflowId,
  selectedTestCaseIds,
  onStartReset,
  onCaseBoundToSwarmRun,
  onRunDone,
  model_id
}: UseMasTestRunStreamArgs) {
  const [masTestRunId, setMasTestRunId] = useState<string | null>(null);
  const [startingTests, setStartingTests] = useState(false);
  const [testCaseTraceRuns, setTestCaseTraceRuns] = useState<Record<string, TestCaseTraceRun>>({});
  const [testCaseRunStatuses, setTestCaseRunStatuses] = useState<Record<string, TestCaseRunStatus>>({});
  const [testCaseDiffs, setTestCaseDiffs] = useState<Record<string, TestCaseDiffState>>({});
  const runStreamRef = useRef<EventSource | null>(null);

// Manages callback.
  const resetTestRunState = useCallback(() => {
    runStreamRef.current?.close();
    setMasTestRunId(null);
    setTestCaseTraceRuns({});
    setTestCaseRunStatuses({});
    setTestCaseDiffs({});
  }, []);

// Manages callback.
  const startSelectedTests = useCallback(async () => {
    if (selectedTestCaseIds.length === 0) return;

    resetTestRunState();
    onStartReset();
    setStartingTests(true);


    try {
      const response = await fetch(`${API_BASE_URL}/api/mas-tests/runs/start`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_id : model_id,
          workflow_id: workflowId,
          case_ids: selectedTestCaseIds,
        }),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || 'Failed to start MAS test run');
      }

      const payload = (await response.json()) as unknown;
      const runId = extractMasTestRunId(payload);
      if (!runId) {
        throw new Error('MAS test run id was not returned');
      }

      setMasTestRunId(runId);

      const source = new EventSource(`${API_BASE_URL}/api/mas-tests/runs/${encodeURIComponent(runId)}/stream`);
      runStreamRef.current = source;

// Parses event payload.
      const parseEventPayload = (event: MessageEvent<string>) => {
        try {
          const parsed = JSON.parse(event.data) as unknown;
          return isRecord(parsed) ? parsed : null;
        } catch {
          return null;
        }
      };

// Handles case start payload.
      const handleCaseStartPayload = (payloadRecord: Record<string, unknown>) => {
        const testCaseId = extractCaseId(payloadRecord);
        const swarmRunId = extractSwarmRunId(payloadRecord);
        if (!testCaseId || !swarmRunId) return;
// Sets test case run statuses.
        setTestCaseRunStatuses((prev) => ({
          ...prev,
          [testCaseId]: 'running',
        }));
// Sets test case trace runs.
        setTestCaseTraceRuns((prev) => ({
          ...prev,
          [testCaseId]: {
            swarmRunId,
            eventsStreamUrl: buildSwarmEventsStreamUrl(API_BASE_URL, swarmRunId),
          },
        }));
        onCaseBoundToSwarmRun(testCaseId, swarmRunId);
      };

// Handles case done payload.
      const handleCaseDonePayload = (payloadRecord: Record<string, unknown>) => {
        const testCaseId = extractCaseId(payloadRecord);
        if (!testCaseId) return;
        const passed = extractPassed(payloadRecord);
        const diff = extractDiff(payloadRecord);
        const score =
          typeof payloadRecord.score === 'number'
            ? payloadRecord.score
            : isRecord(payloadRecord.result) && typeof payloadRecord.result.score === 'number'
              ? payloadRecord.result.score
              : isRecord(payloadRecord.payload_json) && typeof payloadRecord.payload_json.score === 'number'
                ? payloadRecord.payload_json.score
                : null;
        const swarmStatus =
          asString(payloadRecord.swarm_status) ??
          (isRecord(payloadRecord.result) ? asString(payloadRecord.result.swarm_status) : undefined) ??
          (isRecord(payloadRecord.payload_json) ? asString(payloadRecord.payload_json.swarm_status) : undefined) ??
          null;

// Sets test case run statuses.
        setTestCaseRunStatuses((prev) => ({
          ...prev,
          [testCaseId]: passed ? 'passed' : 'failed',
        }));
// Sets test case diffs.
        setTestCaseDiffs((prev) => ({
          ...prev,
          [testCaseId]:
            diff && isRecord(diff)
              ? {
                status: 'ready',
                diff,
                passed,
                score,
                swarmStatus,
              }
              : {
                status: 'idle',
                passed,
                score,
                swarmStatus,
              },
        }));
      };

// Handles add event listener.
      source.addEventListener('case_start', (event) => {
        const payloadRecord = parseEventPayload(event as MessageEvent<string>);
        if (!payloadRecord) return;
        handleCaseStartPayload(payloadRecord);
      });

// Handles add event listener.
      source.addEventListener('case_done', (event) => {
        const payloadRecord = parseEventPayload(event as MessageEvent<string>);
        if (!payloadRecord) return;
        handleCaseDonePayload(payloadRecord);
      });

// Handles add event listener.
      source.addEventListener('message', (event) => {
        const payloadRecord = parseEventPayload(event as MessageEvent<string>);
        if (!payloadRecord) return;

        const eventType =
          asString(payloadRecord.event_type) ??
          (isRecord(payloadRecord.result) ? asString(payloadRecord.result.event_type) : undefined) ??
          (isRecord(payloadRecord.payload_json) ? asString(payloadRecord.payload_json.event_type) : undefined);

        if (eventType === 'case_start') {
          handleCaseStartPayload(payloadRecord);
        }
        if (eventType === 'case_done') {
          handleCaseDonePayload(payloadRecord);
        }
      });

// Handles add event listener.
      source.addEventListener('done', () => {
        source.close();
        if (runStreamRef.current === source) runStreamRef.current = null;
        onRunDone(runId);
      });

// Manages callback.
      source.onerror = () => {
        console.warn('MAS test run stream disconnected; waiting for SSE reconnect');
      };
    } catch (error) {
      console.error('Failed to start MAS test run', error);
    } finally {
      setStartingTests(false);
    }
  }, [model_id, onCaseBoundToSwarmRun, onRunDone, onStartReset, resetTestRunState, selectedTestCaseIds, workflowId]);

// Manages effect.
  useEffect(() => {
// Manages effect.
    return () => {
      runStreamRef.current?.close();
    };
  }, []);

  return {
    masTestRunId,
    startingTests,
    testCaseTraceRuns,
    testCaseRunStatuses,
    testCaseDiffs,
    startSelectedTests,
    resetTestRunState,
  };
}
