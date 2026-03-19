import { JsonInspector } from '../../../shared/ui/JsonInspector';

type TraceOutputHoverBadgeProps = {
  value: unknown;
};

export function TraceOutputHoverBadge({ value }: TraceOutputHoverBadgeProps) {
  const hasValue = value != null && (typeof value !== 'string' || value.trim().length > 0);

  return (
    <span className="group relative inline-flex">
      <span className="inline-flex cursor-default items-center rounded-full bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700 ring-1 ring-sky-200">
        Output
      </span>

      <div className="absolute left-0 top-full z-20 mt-2 hidden w-140 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl group-hover:block group-focus-within:block">
        {hasValue ? (
          <div className="max-h-80 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <JsonInspector value={value} />
          </div>
        ) : (
          <p className="text-xs text-slate-500">No output.</p>
        )}
      </div>
    </span>
  );
}
