import { JsonInspector } from '../../../../shared/ui/JsonInspector';

type AgentRawJsonDetailsProps = {
  summary: string;
  value: unknown;
  className?: string;
  contentClassName?: string;
};

// Renders the agent raw JSON details.
export function AgentRawJsonDetails({
  summary,
  value,
  className = 'rounded-2xl border border-slate-200 bg-white p-4',
  contentClassName = 'mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3',
}: AgentRawJsonDetailsProps) {
  return (
    <details className={className}>
      <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">{summary}</summary>
      <div className={contentClassName}>
        <JsonInspector value={value} />
      </div>
    </details>
  );
}
