import { AgentStatCard } from '../../agents/components/shared/AgentStatCard';

type MasResultsTabProps = {
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asStringArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function FieldSection({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className="text-sm leading-6 text-slate-700">{value}</p>
    </div>
  );
}

function ListSection({
  label,
  items,
}: {
  label: string;
  items: string[];
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      {items.length ? (
        <ul className="space-y-2 text-sm text-slate-700">
          {items.map((item, index) => (
            <li key={`${label}-${index}`} className="rounded-xl border border-slate-200 bg-white px-3 py-2">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">None</p>
      )}
    </div>
  );
}

export default function MasResultsTab({ output }: MasResultsTabProps) {
  const outputJson = output && isRecord(output.output_json) ? output.output_json : null;

  const finalEsiLevel =
    outputJson && typeof outputJson.final_esi_level === 'number' ? outputJson.final_esi_level : null;
  const decisionSource =
    outputJson && typeof outputJson.decision_source === 'string' ? outputJson.decision_source : 'Unknown';
  const summary =
    outputJson && typeof outputJson.summary === 'string' ? outputJson.summary : 'No summary available.';
  const rationale =
    outputJson && typeof outputJson.rationale === 'string' ? outputJson.rationale : 'No rationale available.';
  const uptriaged =
    outputJson && typeof outputJson.uptriaged === 'boolean' ? outputJson.uptriaged : null;
  const keyConcerns = outputJson ? asStringArray(outputJson.key_concerns) : [];
  const predictedResources = outputJson ? asStringArray(outputJson.predicted_resources) : [];
  const abnormalVitals = outputJson ? asStringArray(outputJson.abnormal_vitals_considered) : [];
  const nextActions = outputJson ? asStringArray(outputJson.next_actions) : [];

  return (
    <div className="flex h-full min-h-0 overflow-hidden bg-white">
      <div className="flex h-full min-h-0 w-full flex-col overflow-hidden p-4">
        <p className='text-slate-900 font-medium text-xl mb-2'>Mas Output</p>
        <div className="min-h-0 flex-1 overflow-y-auto pr-2 pb-6">
          {outputJson ? (
            <div className="space-y-6">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <AgentStatCard
                  label="Final ESI Level"
                  value={finalEsiLevel != null ? String(finalEsiLevel) : '—'}
                  tone="accent"
                />
                <AgentStatCard label="Decision Source" value={decisionSource} small={true} />
                <AgentStatCard
                  label="Uptriaged"
                  value={uptriaged == null ? 'Unknown' : uptriaged ? 'Yes' : 'No'}
                  tone={uptriaged == null ? 'default' : uptriaged ? 'warning' : 'positive'}
                />
              </div>

              <FieldSection label="Summary" value={summary} />
              <FieldSection label="Rationale" value={rationale} />
              <ListSection label="Key Concerns" items={keyConcerns} />
              <ListSection label="Predicted Resources" items={predictedResources} />
              <ListSection label="Abnormal Vitals Considered" items={abnormalVitals} />
              <ListSection label="Next Actions" items={nextActions} />
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
              <p className="text-sm font-semibold text-slate-900">No MAS Output</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
