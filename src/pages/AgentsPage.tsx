import { AgentCard } from '../components/AgentCard';

export function AgentsPage() {
  return (
    <section aria-label="Agents" className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <AgentCard title="Vitals Agent" toolsCount={4} testCasesCount={7} />
    </section>
  );
}
