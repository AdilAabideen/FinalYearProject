import { asString, isRecord } from './runResult';

type RunMetrics = {
  total?: number;
  passed?: number;
  failed?: number;
  exec_failed?: number;
  invalid_pred?: number;
  pass_rate?: number;
  classification?: {
    label?: string;
    tp?: number;
    tn?: number;
    fp?: number;
    fn?: number;
    n_eval?: number;
    accuracy?: number;
    precision?: number | null;
    recall?: number | null;
    f1?: number | null;
    specificity?: number | null;
    excluded?: {
      exec_failed?: number;
      invalid_pred?: number;
      other?: number;
    };
  };
};

export function extractCaseId(payload: Record<string, unknown>) {
  return (
    asString(payload.test_case_id) ??
    asString(payload.case_id) ??
    (isRecord(payload.result)
      ? asString(payload.result.test_case_id) ?? asString(payload.result.case_id)
      : undefined) ??
    (isRecord(payload.payload_json)
      ? asString(payload.payload_json.test_case_id) ?? asString(payload.payload_json.case_id)
      : undefined)
  );
}

export function extractAgentRunId(payload: Record<string, unknown>) {
  return (
    asString(payload.agent_run_id) ??
    asString(payload.run_id) ??
    (isRecord(payload.result)
      ? asString(payload.result.agent_run_id) ?? asString(payload.result.run_id)
      : undefined) ??
    (isRecord(payload.payload_json)
      ? asString(payload.payload_json.agent_run_id) ?? asString(payload.payload_json.run_id)
      : undefined)
  );
}

export function extractPassed(payload: Record<string, unknown>) {
  if (typeof payload.passed === 'boolean') return payload.passed;
  const status =
    asString(payload.status) ??
    (isRecord(payload.result) ? asString(payload.result.status) : undefined) ??
    (isRecord(payload.payload_json) ? asString(payload.payload_json.status) : undefined) ??
    '';
  return status.toLowerCase().includes('pass');
}

export function extractMetrics(payload: Record<string, unknown>) {
  if (isRecord(payload.metrics)) return payload.metrics as RunMetrics;
  if (isRecord(payload.metrics_json)) return payload.metrics_json as RunMetrics;
  if (isRecord(payload.result) && isRecord(payload.result.metrics)) {
    return payload.result.metrics as RunMetrics;
  }
  return null;
}

export function extractDiff(payload: Record<string, unknown>) {
  if (isRecord(payload.diff_json)) return payload.diff_json;
  if (isRecord(payload.result) && isRecord(payload.result.diff_json)) return payload.result.diff_json;
  if (isRecord(payload.payload_json) && isRecord(payload.payload_json.diff_json)) {
    return payload.payload_json.diff_json;
  }
  return null;
}
