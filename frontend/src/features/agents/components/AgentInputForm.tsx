import { useId } from 'react';
import { cn } from '../../../shared/lib/cn';
import {
  getEnumValues,
  getNumberConstraint,
  getObjectSchema,
  getPattern,
  getPrimaryType,
  getSchemaDescription,
  getSchemaTitle,
  getStringConstraint,
  getStringFormat,
  resolveSchema,
  shouldUseTextArea,
  type JsonSchema,
} from '../utils/jsonSchema';

type AgentInputFormProps = {
  schema: JsonSchema;
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  submitButtonLabel?: string;
  onSubmit?: () => void;
  className?: string;
};

// Handles humanize key.
function humanizeKey(key: string) {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Handles safe ID segment.
function safeIdSegment(value: string) {
  return value.replace(/[^a-zA-Z0-9_-]+/g, '-');
}

// Renders the field wrapper.
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
      <label
        className="flex items-baseline justify-between gap-3 text-xs font-semibold text-slate-700"
        htmlFor={htmlFor}
      >
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

// Renders the agent input form.
export function AgentInputForm({
  schema,
  value,
  onChange,
  submitButtonLabel,
  onSubmit,
  className,
}: AgentInputFormProps) {
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
    <div className={cn('flex min-h-0 flex-col overflow-hidden ', className)}>
      <div className="min-h-0 flex-1 overflow-auto mt-4">
        <div className="grid gap-4 p-4 pt-0 sm:grid-cols-2">
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
                      {description ? (
                        <p className="mt-1 text-sm text-slate-600">{description}</p>
                      ) : null}
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
              const stringValue =
                typeof current === 'string' ? current : current == null ? '' : String(current);

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
              const stringValue =
                typeof current === 'string' ? current : current == null ? '' : String(current);
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
                    className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
                    value={stringValue}
                    onChange={(e) => onChange({ ...value, [fieldKey]: e.target.value })}
                  />
                </FieldWrapper>
              );
            }

            if (primaryType === 'string') {
              const current = value[fieldKey];
              const stringValue =
                typeof current === 'string' ? current : current == null ? '' : String(current);
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
                      className="min-h-24 w-full resize-y rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
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
                      className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
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

      {submitButtonLabel ? (
        <div className="shrink-0 border-t border-slate-200 bg-white p-3">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onSubmit}
              className="rounded-xl bg-PrimaryBlue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-PrimaryBlue/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
            >
              {submitButtonLabel}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
