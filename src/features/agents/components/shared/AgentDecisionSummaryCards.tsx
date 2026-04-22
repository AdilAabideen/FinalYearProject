import { Badge } from '../../../../shared/ui/Badge';
import type { DecisionTone } from '../../utils/runResult';
import { AgentStatCard } from './AgentStatCard';

type AgentDecisionSummaryCardsProps = {
  decisionLabel: string;
  decisionTone: DecisionTone;
  confidenceLabel: string;
};

export function AgentDecisionSummaryCards({
  decisionLabel,
  decisionTone,
  confidenceLabel,
}: AgentDecisionSummaryCardsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-2">
      <AgentStatCard
        label="Decision"
        value={decisionLabel}
        tone={decisionTone === 'positive' ? 'positive' : decisionTone === 'danger' ? 'danger' : 'default'}
      />
      <AgentStatCard label="Confidence" value={confidenceLabel} tone="accent" />
    </div>
  );
}

type AgentNarrativeSectionsProps = {
  caseSummary: string;
  justification: string;
  risks: string[];
  missingInformation: string[];
};

export function AgentNarrativeSections({
  caseSummary,
  justification,
  risks,
  missingInformation,
}: AgentNarrativeSectionsProps) {
  return (
    <section className="grid gap-4 xl:grid-cols-2">
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Clinical Summary</h5>
        <p className="mt-2 text-sm leading-relaxed text-slate-800">{caseSummary}</p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Justification</h5>
        <p className="mt-2 text-sm leading-relaxed text-slate-800">{justification}</p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Key Risks</h5>
        {risks.length ? (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-800">
            {risks.map((risk, index) => (
              <li key={`risk-${index}`}>{risk}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-slate-500">No key risks were returned.</p>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Missing Information</h5>
        {missingInformation.length ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {missingInformation.map((item, index) => (
              <Badge key={`missing-${index}`} className="bg-amber-50 text-amber-700 ring-amber-200">
                {item}
              </Badge>
            ))}
          </div>
        ) : (
          <div className="mt-2">
            <Badge className="bg-emerald-50 text-emerald-700 ring-emerald-200">None detected</Badge>
          </div>
        )}
      </div>
    </section>
  );
}
