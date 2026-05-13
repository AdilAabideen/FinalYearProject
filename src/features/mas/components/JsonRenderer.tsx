type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

type JsonRendererProps = {
  value: unknown;
  title?: string;
};

// Handles humanize key.
function humanizeKey(key: string) {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

// Formats special output.
function formatSpecialOutput(value: string) {
  const match = value.match(/^(not_)?esi(\d+)$/i);
  if (!match) return value;

  const [, negatedPrefix, esiNumber] = match;
  return `${negatedPrefix ? 'Not ' : ''}Esi ${esiNumber}`;
}

// Checks record.
function isRecord(value: unknown): value is { [key: string]: JsonValue } {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// Normalizes value.
function normalizeValue(value: unknown): JsonValue {
  if (
    value == null ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return value as JsonValue;
  }

  if (Array.isArray(value)) {
    return value.map((item) => normalizeValue(item));
  }

  if (typeof value === 'object') {
    const output: Record<string, JsonValue> = {};
    for (const [key, item] of Object.entries(value)) {
      output[key] = normalizeValue(item);
    }
    return output;
  }

  return String(value);
}

// Renders the primitive value.
function PrimitiveValue({ value }: { value: string | number | boolean | null }) {
  if (typeof value === 'boolean') {
    return (
      <span
        className={[
          'inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold ring-1',
          value
            ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
            : 'bg-slate-100 text-slate-600 ring-slate-200',
        ].join(' ')}
      >
        {String(value)}
      </span>
    );
  }

  if (value === null) {
    return (
      <span className="inline-flex w-fit rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500 ring-1 ring-slate-200">
        null
      </span>
    );
  }

  if (typeof value === 'number') {
    return <p className="text-sm font-medium text-slate-900">{value}</p>;
  }

  return <p className="text-sm leading-6 text-slate-700">{formatSpecialOutput(value)}</p>;
}

// Renders the JSON node.
function JsonNode({ value, label }: { value: JsonValue; label?: string }) {
  if (Array.isArray(value)) {
    return (
      <div className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
        {label ? <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p> : null}
        {value.length === 0 ? (
          <p className="text-sm text-slate-500">No items</p>
        ) : (
          value.map((item, index) => (
            <div key={`${label ?? 'item'}-${index}`} className="rounded-xl border border-slate-200 bg-white p-3">
              <JsonNode value={item} />
            </div>
          ))
        )}
      </div>
    );
  }

  if (isRecord(value)) {
    const entries = Object.entries(value);

    return (
      <div className="flex flex-col gap-3">
        {label ? <p className="text-xs font-semibold uppercase text-slate-500">{label}</p> : null}
        {entries.length === 0 ? (
          <div className=" border-slate-200 bg-slate-50 p-2 text-sm text-slate-500">
            Empty object
          </div>
        ) : (
          entries.map(([key, itemValue]) => (
            <div key={key} className="rounded-lg border border-slate-300 bg-white p-3">
              <div className="flex flex-col gap-2">
                <p className="text-sm font-semibold uppercase  text-slate-500">
                  {humanizeKey(key)}
                </p>
                <JsonNode value={itemValue} />
              </div>
            </div>
          ))
        )}
      </div>
    );
  }

  return <PrimitiveValue value={value} />;
}

// Renders the JSON renderer.
export default function JsonRenderer({ value, title = 'JSON Data' }: JsonRendererProps) {
  const normalizedValue = normalizeValue(value);

  return (
    <section className="flex flex-col gap-4 border border-slate-200 bg-white  ">
      <div className="border-b border-slate-200 p-3 ">
        <p className="text-sm font-semibold text-slate-900 ">{title}</p>
      </div>

      <div className="flex flex-col gap-3 p-3 pt-0">
        <JsonNode value={normalizedValue} />
      </div>
    </section>
  );
}
