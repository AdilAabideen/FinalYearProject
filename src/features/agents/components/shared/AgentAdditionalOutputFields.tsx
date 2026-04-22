import { JsonInspector } from '../../../../shared/ui/JsonInspector';
import { titleCaseKey } from '../../utils/format';

type AgentAdditionalOutputFieldsProps = {
  entries: Array<[string, unknown]>;
  summaryLabel?: string;
};

export function AgentAdditionalOutputFields({
  entries,
  summaryLabel = 'Additional Output Fields',
}: AgentAdditionalOutputFieldsProps) {
  if (!entries.length) return null;

  return (
    <details className="rounded-2xl border border-slate-200 bg-white p-4">
      <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
        {summaryLabel}
      </summary>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {entries.map(([key, item]) => (
          <div key={key} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {titleCaseKey(key)}
            </p>
            <div className="mt-2 max-h-40 overflow-auto text-sm text-slate-800">
              {item != null && typeof item === 'object' ? <JsonInspector value={item} /> : <p>{String(item ?? '—')}</p>}
            </div>
          </div>
        ))}
      </div>
    </details>
  );
}
