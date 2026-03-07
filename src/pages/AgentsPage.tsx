import { AgentCard } from '../components/AgentCard';
import { SectionHeader } from '../components/layout/SectionHeader';

export function AgentsPage() {
  return (
    <section aria-label="Agents">
      <div className="space-y-6">

        <div className="grid items-start gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <AgentCard title="Vitals Agent" toolsCount={4} testCasesCount={7} />
        </div>
      </div>
    </section>
  );
}
