import type { DecisionTone } from '../../utils/runResult';
import { AgentStatCard } from './AgentStatCard';

type AgentDecisionSummaryCardsProps = {
  decisionLabel: string;
  decisionTone: DecisionTone;
  confidenceLabel: string;
};

// Renders the agent decision summary cards.
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
