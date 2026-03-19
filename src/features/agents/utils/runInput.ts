import type { AgentCatalogDetail } from '../../../types/agents';
import { getPrimaryType, getStringFormat, isRecord } from './jsonSchema';

export function getDefaultInputs(agent: AgentCatalogDetail): Record<string, unknown> {
  if (agent.name !== 'vitals_agent') return {};

  return {
    temperature: '98.3',
    heartrate: '75',
    resprate: '14',
    o2sat: '100',
    sbp: '138',
    dbp: '90',
    pain: '7',
    subject_id: '19880634',
    intime: '2199-10-08T16:40',
    age_years: '49.7',
    chiefcomplaint: 'Left Abdominal Pain',
  };
}

export function coerceInputForRun(inputSchema: Record<string, unknown>, raw: Record<string, unknown>) {
  const properties = isRecord(inputSchema.properties) ? inputSchema.properties : {};
  const required = new Set(
    Array.isArray(inputSchema.required)
      ? inputSchema.required.filter((k): k is string => typeof k === 'string' && k.length > 0)
      : [],
  );

  const output: Record<string, unknown> = {};

  for (const [key, schema] of Object.entries(properties)) {
    const rawValue = raw[key];

    if (rawValue == null || rawValue === '') {
      if (required.has(key)) throw new Error(`Missing required field: ${key}`);
      continue;
    }

    const primaryType = getPrimaryType(inputSchema, schema);
    const stringFormat = getStringFormat(inputSchema, schema);

    if ((primaryType === 'number' || primaryType === 'integer') && typeof rawValue === 'string') {
      const num = Number(rawValue);
      if (!Number.isFinite(num)) throw new Error(`Invalid number for ${key}`);
      output[key] = primaryType === 'integer' ? Math.trunc(num) : num;
      continue;
    }

    if (primaryType === 'integer' && typeof rawValue === 'number') {
      output[key] = Math.trunc(rawValue);
      continue;
    }

    if (primaryType === 'number' && typeof rawValue === 'number') {
      output[key] = rawValue;
      continue;
    }

    if (primaryType === 'string' && stringFormat === 'date-time' && typeof rawValue === 'string') {
      output[key] = rawValue;
      continue;
    }

    output[key] = rawValue;
  }

  return output;
}
