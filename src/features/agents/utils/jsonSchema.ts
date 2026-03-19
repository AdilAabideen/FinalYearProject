export type JsonSchema = Record<string, unknown>;

export type ResolvedObjectSchema = {
  title?: string;
  description?: string;
  properties: Record<string, unknown>;
  required: Set<string>;
};

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function decodeJsonPointerToken(token: string) {
  return token.replace(/~1/g, '/').replace(/~0/g, '~');
}

function resolveJsonPointer(root: unknown, pointer: string): unknown {
  if (!pointer.startsWith('#/')) return undefined;
  const parts = pointer
    .slice(2)
    .split('/')
    .filter(Boolean)
    .map((part) => decodeJsonPointerToken(part));

  let current: unknown = root;
  for (const part of parts) {
    if (!isRecord(current)) return undefined;
    current = current[part];
  }
  return current;
}

export function resolveSchema(root: unknown, schema: unknown) {
  let current = schema;
  const visited = new Set<unknown>();

  for (let i = 0; i < 25; i += 1) {
    if (!isRecord(current)) return current;
    const ref = current.$ref;
    if (typeof ref !== 'string' || !ref.length) return current;

    const resolved = resolveJsonPointer(root, ref);
    if (!resolved || visited.has(resolved)) return current;

    visited.add(resolved);
    current = resolved;
  }

  return current;
}

export function getSchemaTitle(schema: unknown): string | undefined {
  if (!isRecord(schema)) return undefined;
  return typeof schema.title === 'string' && schema.title.trim().length ? schema.title : undefined;
}

export function getSchemaDescription(schema: unknown): string | undefined {
  if (!isRecord(schema)) return undefined;
  return typeof schema.description === 'string' && schema.description.trim().length
    ? schema.description
    : undefined;
}

export function getRequiredSet(schema: unknown) {
  if (!isRecord(schema)) return new Set<string>();
  const required = schema.required;
  if (!Array.isArray(required)) return new Set<string>();

  const keys = required.filter((key): key is string => typeof key === 'string' && key.length > 0);
  return new Set(keys);
}

export function getObjectSchema(root: unknown, schema: unknown): ResolvedObjectSchema | null {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return null;

  const properties = resolved.properties;
  if (!isRecord(properties) || Object.keys(properties).length === 0) return null;

  return {
    title: getSchemaTitle(resolved),
    description: getSchemaDescription(resolved),
    properties,
    required: getRequiredSet(resolved),
  };
}

export function getTypeCandidates(root: unknown, schema: unknown): string[] {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return [];

  const directType = resolved.type;
  const types: string[] = [];

  if (typeof directType === 'string') types.push(directType);
  if (Array.isArray(directType)) {
    for (const t of directType) if (typeof t === 'string') types.push(t);
  }

  const unions = resolved.anyOf ?? resolved.oneOf;
  if (Array.isArray(unions)) {
    for (const option of unions) types.push(...getTypeCandidates(root, option));
  }

  return Array.from(new Set(types));
}

export function getPrimaryType(root: unknown, schema: unknown) {
  const types = getTypeCandidates(root, schema).filter((t) => t !== 'null');
  if (types.length === 1) return types[0];
  if (types.length === 0) return undefined;
  return 'unknown';
}

export function getEnumValues(root: unknown, schema: unknown): unknown[] | null {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return null;
  return Array.isArray(resolved.enum) && resolved.enum.length ? resolved.enum : null;
}

export function getStringFormat(root: unknown, schema: unknown): string | undefined {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return undefined;
  return typeof resolved.format === 'string' && resolved.format.trim().length ? resolved.format : undefined;
}

export function getNumberConstraint(root: unknown, schema: unknown, key: 'minimum' | 'maximum') {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return undefined;
  const value = resolved[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

export function getStringConstraint(root: unknown, schema: unknown, key: 'minLength' | 'maxLength') {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return undefined;
  const value = resolved[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

export function getPattern(root: unknown, schema: unknown): string | undefined {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return undefined;
  return typeof resolved.pattern === 'string' && resolved.pattern.trim().length ? resolved.pattern : undefined;
}

export function shouldUseTextArea(fieldKey: string, root: unknown, schema: unknown) {
  const resolved = resolveSchema(root, schema);
  if (isRecord(resolved) && resolved.contentMediaType) return true;
  return /(complaint|description|notes?|message|text|prompt)/i.test(fieldKey);
}
