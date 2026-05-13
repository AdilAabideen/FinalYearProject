// Provides stream parsers helpers.
import { asString, isRecord } from '../../agents/utils/runResult';

// Extracts MAS test run ID.
export function extractMasTestRunId(value: unknown) {
  if (!isRecord(value)) return null;

  return (
    asString(value.run_id) ??
    asString(value.id) ??
    (isRecord(value.result) ? asString(value.result.run_id) ?? asString(value.result.id) : undefined) ??
    null
  );
}

// Extracts swarm run ID.
export function extractSwarmRunId(value: Record<string, unknown>) {
  return (
    asString(value.swarm_run_id) ??
    (isRecord(value.result) ? asString(value.result.swarm_run_id) : undefined) ??
    (isRecord(value.payload_json) ? asString(value.payload_json.swarm_run_id) : undefined) ??
    null
  );
}
