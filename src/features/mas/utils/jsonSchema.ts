// Provides JSON schema helpers.
import { getStringFormat, getTypeCandidates, isRecord } from '../../agents/utils/jsonSchema';

// Gets coercion type.
function getCoercionType(root: Record<string, unknown>, schema: unknown) {
// Handles filter.
  const types = getTypeCandidates(root, schema).filter((t) => t !== 'null');

  if (types.length === 0) return undefined;
  if (types.length === 1) return types[0];

  // Treat numeric unions as numbers so HTML number inputs can be coerced safely.
  if (types.every((t) => t === 'number' || t === 'integer')) {
    return 'number';
  }

  return 'unknown';
}

// Checks nullable schema.
function isNullableSchema(root: Record<string, unknown>, schema: unknown) {
  return getTypeCandidates(root, schema).includes('null');
}

// Checks empty input value.
function isEmptyInputValue(value: unknown) {
  return value == null || (typeof value === 'string' && value.trim() === '');
}

// Handles coerce input for run.
export function coerceInputForRun(
  inputSchema: Record<string, unknown>,
  raw: Record<string, unknown>,
) {
  const properties = isRecord(inputSchema.properties) ? inputSchema.properties : {};
  const output: Record<string, unknown> = {};

  for (const [key, schema] of Object.entries(properties)) {
    const rawValue = raw[key];

    if (isEmptyInputValue(rawValue)) {
      if (isNullableSchema(inputSchema, schema)) output[key] = null;
      continue;
    }

    const type = getCoercionType(inputSchema, schema);
    const stringFormat = getStringFormat(inputSchema, schema);

    if ((type === 'number' || type === 'integer') && typeof rawValue === 'string') {
      const num = Number(rawValue);
      if (!Number.isFinite(num)) {
        throw new Error(`Invalid number for ${key}`);
      }
      output[key] = type === 'integer' ? Math.trunc(num) : num;
      continue;
    }

    if (type === 'integer' && typeof rawValue === 'number') {
      output[key] = Math.trunc(rawValue);
      continue;
    }

    if (type === 'number' && typeof rawValue === 'number') {
      output[key] = rawValue;
      continue;
    }

    if (type === 'boolean' && typeof rawValue === 'string') {
      if (rawValue === 'true') {
        output[key] = true;
        continue;
      }
      if (rawValue === 'false') {
        output[key] = false;
        continue;
      }
    }

    if (type === 'string' && stringFormat === 'date-time' && typeof rawValue === 'string') {
      output[key] = rawValue;
      continue;
    }

    output[key] = rawValue;
  }

  return output;
}
