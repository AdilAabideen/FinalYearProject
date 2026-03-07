import { AgentCard } from '../components/AgentCard';

export function AgentsPage() {
  return (
    <section aria-label="Agents">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-slate-900">Available Agents</h2>
        <p className="mt-1 text-sm text-slate-600">
          Select an agent to view its tools and test cases. Backend metadata integration coming next.
        </p>
      </div>

      <div className="grid items-start gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <AgentCard title="Vitals Agent" toolsCount={4} testCasesCount={7} />
      </div>
    </section>
  );
}
