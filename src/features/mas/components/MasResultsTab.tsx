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

function formatSnakeCaseLabel(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
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
      <p className="text-sm font-semibold uppercase  text-slate-500">{label}</p>
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
      <p className="text-sm font-semibold uppercase  text-slate-500">{label}</p>
      {items.length ? (
        <ul className="space-y-2 text-sm text-slate-700">
          {items.map((item, index) => (
            <li key={`${label}-${index}`} className="rounded-lg border border-slate-300 bg-white px-3 py-2">
              {item.slice(0,1).toUpperCase() + item.slice(1)}
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
      <div className="flex h-full min-h-0 w-full flex-col overflow-hidden">
        <p className='text-xl font-semibold text-slate-900 mb-2 border-b border-slate-200 p-3 '>Mas Output</p>
        <div className="min-h-0 flex-1 overflow-y-auto pr-2 pb-6 p-3">
          {outputJson ? (
            <div className="space-y-6">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <AgentStatCard
                  label="Final ESI Level"
                  value={finalEsiLevel != null ? String(finalEsiLevel) : '—'}
                  tone="accent"
                />
                <AgentStatCard label="Decision Source" value={formatSnakeCaseLabel(decisionSource)} small={true} />
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
            <div className=" px-2">
              <p className="text-md  text-slate-800">No Mas Output Please Run a Test Case to get outputs</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
