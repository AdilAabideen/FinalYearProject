import { useId } from 'react';
import { cn } from '../../lib/cn';

type JsonSchema = Record<string, unknown>;

type AgentInputFormProps = {
  schema: JsonSchema;
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
};

type ResolvedObjectSchema = {
  title?: string;
  description?: string;
  properties: Record<string, unknown>;
  required: Set<string>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
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

function resolveSchema(root: unknown, schema: unknown) {
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

function getSchemaTitle(schema: unknown): string | undefined {
  if (!isRecord(schema)) return undefined;
  return typeof schema.title === 'string' && schema.title.trim().length ? schema.title : undefined;
}

function getSchemaDescription(schema: unknown): string | undefined {
  if (!isRecord(schema)) return undefined;
  return typeof schema.description === 'string' && schema.description.trim().length
    ? schema.description
    : undefined;
}

function getRequiredSet(schema: unknown) {
  if (!isRecord(schema)) return new Set<string>();
  const required = schema.required;
  if (!Array.isArray(required)) return new Set<string>();

  const keys = required.filter((key): key is string => typeof key === 'string' && key.length > 0);
  return new Set(keys);
}

function getObjectSchema(root: unknown, schema: unknown): ResolvedObjectSchema | null {
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

function humanizeKey(key: string) {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function safeIdSegment(value: string) {
  return value.replace(/[^a-zA-Z0-9_-]+/g, '-');
}

function getTypeCandidates(root: unknown, schema: unknown): string[] {
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

function getPrimaryType(root: unknown, schema: unknown) {
  const types = getTypeCandidates(root, schema).filter((t) => t !== 'null');
  if (types.length === 1) return types[0];
  if (types.length === 0) return undefined;
  return 'unknown';
}

function getEnumValues(root: unknown, schema: unknown): unknown[] | null {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return null;
  return Array.isArray(resolved.enum) && resolved.enum.length ? resolved.enum : null;
}

function getStringFormat(root: unknown, schema: unknown): string | undefined {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return undefined;
  return typeof resolved.format === 'string' && resolved.format.trim().length ? resolved.format : undefined;
}

function getNumberConstraint(root: unknown, schema: unknown, key: 'minimum' | 'maximum') {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return undefined;
  const value = resolved[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function getStringConstraint(root: unknown, schema: unknown, key: 'minLength' | 'maxLength') {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return undefined;
  const value = resolved[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function getPattern(root: unknown, schema: unknown): string | undefined {
  const resolved = resolveSchema(root, schema);
  if (!isRecord(resolved)) return undefined;
  return typeof resolved.pattern === 'string' && resolved.pattern.trim().length ? resolved.pattern : undefined;
}

function shouldUseTextArea(fieldKey: string, root: unknown, schema: unknown) {
  const resolved = resolveSchema(root, schema);
  if (isRecord(resolved)) {
    if (resolved.contentMediaType) return true;
  }

  return /(complaint|description|notes?|message|text|prompt)/i.test(fieldKey);
}

function FieldWrapper({
  label,
  required,
  description,
  htmlFor,
  fullWidth,
  children,
}: {
  label: string;
  required: boolean;
  description?: string;
  htmlFor: string;
  fullWidth?: boolean;
  children: React.ReactNode;
}) {
  const descriptionId = description ? `${htmlFor}-help` : undefined;

  return (
    <div className={cn('space-y-1', fullWidth && 'sm:col-span-2')}>
      <label className="flex items-baseline justify-between gap-3 text-xs font-semibold text-slate-700" htmlFor={htmlFor}>
        <span className="truncate">
          {label}
          {required ? <span className="ml-1 text-rose-600">*</span> : null}
        </span>
      </label>
      {children}
      {description ? (
        <p id={descriptionId} className="text-xs text-slate-500">
          {description}
        </p>
      ) : null}
    </div>
  );
}

export function AgentInputForm({ schema, value, onChange }: AgentInputFormProps) {
  const baseId = useId();
  const objectSchema = getObjectSchema(schema, schema);

  if (!objectSchema) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
        This agent does not require any inputs.
      </div>
    );
  }

  return (
    <div className="space-y-4">


      <div className="grid gap-4 sm:grid-cols-2">
        {Object.entries(objectSchema.properties).map(([fieldKey, fieldSchema]) => {
          const resolved = resolveSchema(schema, fieldSchema);
          const required = objectSchema.required.has(fieldKey);
          const enumValues = getEnumValues(schema, resolved);
          const title = getSchemaTitle(resolved) ?? humanizeKey(fieldKey);
          const description = getSchemaDescription(resolved);
          const fieldId = `${baseId}-${safeIdSegment(fieldKey)}`;

          const primaryType = getPrimaryType(schema, resolved);
          const stringFormat = getStringFormat(schema, resolved);

          if (primaryType === 'boolean') {
            const checked = Boolean(value[fieldKey]);
            return (
              <div key={fieldKey} className="sm:col-span-2">
                <label
                  htmlFor={fieldId}
                  className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900">
                      {title}
                      {required ? <span className="ml-1 text-rose-600">*</span> : null}
                    </p>
                    {description ? <p className="mt-1 text-sm text-slate-600">{description}</p> : null}
                  </div>
                  <input
                    id={fieldId}
                    name={fieldKey}
                    type="checkbox"
                    className="mt-1 h-5 w-5 rounded-md border-slate-300 text-PrimaryBlue focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                    checked={checked}
                    onChange={(e) => onChange({ ...value, [fieldKey]: e.target.checked })}
                  />
                </label>
              </div>
            );
          }

          if (enumValues) {
            const current = value[fieldKey];
            const stringValue = typeof current === 'string' ? current : current == null ? '' : String(current);

            return (
              <FieldWrapper
                key={fieldKey}
                htmlFor={fieldId}
                label={title}
                required={required}
                description={description}
                fullWidth={shouldUseTextArea(fieldKey, schema, resolved)}
              >
                <select
                  id={fieldId}
                  name={fieldKey}
                  required={required}
                  className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                  value={stringValue}
                  onChange={(e) => onChange({ ...value, [fieldKey]: e.target.value })}
                >
                  {required ? null : <option value="">—</option>}
                  {enumValues.map((option) => {
                    const optionValue =
                      typeof option === 'string' ? option : option == null ? '' : String(option);
                    return (
                      <option key={optionValue} value={optionValue}>
                        {optionValue}
                      </option>
                    );
                  })}
                </select>
              </FieldWrapper>
            );
          }

          if (primaryType === 'integer' || primaryType === 'number') {
            const current = value[fieldKey];
            const stringValue = typeof current === 'string' ? current : current == null ? '' : String(current);
            const minimum = getNumberConstraint(schema, resolved, 'minimum');
            const maximum = getNumberConstraint(schema, resolved, 'maximum');

            return (
              <FieldWrapper
                key={fieldKey}
                htmlFor={fieldId}
                label={title}
                required={required}
                description={description}
              >
                <input
                  id={fieldId}
                  name={fieldKey}
                  type="number"
                  step={primaryType === 'integer' ? 1 : 'any'}
                  min={minimum}
                  max={maximum}
                  required={required}
                  className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700  placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                  value={stringValue}
                  onChange={(e) => onChange({ ...value, [fieldKey]: e.target.value })}
                />
              </FieldWrapper>
            );
          }

          if (primaryType === 'string') {
            const current = value[fieldKey];
            const stringValue = typeof current === 'string' ? current : current == null ? '' : String(current);
            const minLength = getStringConstraint(schema, resolved, 'minLength');
            const maxLength = getStringConstraint(schema, resolved, 'maxLength');
            const pattern = getPattern(schema, resolved);
            const multiline = shouldUseTextArea(fieldKey, schema, resolved);

            const inputType =
              stringFormat === 'date-time'
                ? 'datetime-local'
                : stringFormat === 'date'
                  ? 'date'
                  : stringFormat === 'time'
                    ? 'time'
                    : 'text';

            return (
              <FieldWrapper
                key={fieldKey}
                htmlFor={fieldId}
                label={title}
                required={required}
                description={description}
                fullWidth={multiline}
              >
                {multiline ? (
                  <textarea
                    id={fieldId}
                    name={fieldKey}
                    required={required}
                    minLength={minLength}
                    maxLength={maxLength}
                    className="min-h-24 w-full resize-y rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700  placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                    value={stringValue}
                    onChange={(e) => onChange({ ...value, [fieldKey]: e.target.value })}
                  />
                ) : (
                  <input
                    id={fieldId}
                    name={fieldKey}
                    type={inputType}
                    required={required}
                    minLength={minLength}
                    maxLength={maxLength}
                    pattern={pattern}
                    className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700  placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                    value={stringValue}
                    onChange={(e) => onChange({ ...value, [fieldKey]: e.target.value })}
                  />
                )}
              </FieldWrapper>
            );
          }

          const fallbackValue = value[fieldKey];
          const stringValue =
            typeof fallbackValue === 'string'
              ? fallbackValue
              : fallbackValue == null
                ? ''
                : JSON.stringify(fallbackValue, null, 2);

          return (
            <FieldWrapper
              key={fieldKey}
              htmlFor={fieldId}
              label={title}
              required={required}
              description={description ?? 'Unsupported schema type. Provide raw JSON.'}
              fullWidth
            >
              <textarea
                id={fieldId}
                name={fieldKey}
                required={required}
                className="min-h-24 w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 font-mono text-xs text-slate-700 shadow-sm placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                value={stringValue}
                onChange={(e) => onChange({ ...value, [fieldKey]: e.target.value })}
              />
            </FieldWrapper>
          );
        })}
      </div>
    </div>
  );
}
