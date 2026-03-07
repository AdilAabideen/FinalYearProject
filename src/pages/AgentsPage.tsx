import { useEffect, useMemo, useState } from 'react';
import { agentDiscoveryService } from '../services/agentDiscoveryService';
import type { AgentCatalogSummary } from '../types/agents';
import { AgentCard, AgentCardSkeleton } from '../components/AgentCard';

type AgentsLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; agents: AgentCatalogSummary[] };

export function AgentsPage() {
  const [state, setState] = useState<AgentsLoadState>({ status: 'loading' });

  useEffect(() => {
    const ac = new AbortController();

    async function loadAgents() {
      try {
        const data = await agentDiscoveryService.listAgents(ac.signal);
        if (!ac.signal.aborted) {
          setState({ status: 'success', agents: data });
        }
      } catch (e: unknown) {
        if (ac.signal.aborted) return;
        setState({
          status: 'error',
          message: e instanceof Error ? e.message : 'Failed to load agents',
        });
      }
    }

    loadAgents();

    return () => ac.abort();
  }, []);

  const skeletons = useMemo(() => Array.from({ length: 6 }, (_, i) => i), []);

  return (
    <section aria-label="Agents">
      <div className="space-y-6">
        {/* <SectionHeader
          title="Available Agents"
          description="Browse all available agents in the system."
        /> */}

        {state.status === 'error' ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {state.message}
          </div>
        ) : null}

        <div className="grid items-start gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {state.status === 'success'
            ? state.agents.map((agent) => (
                <AgentCard
                  key={agent.name}
                  name={agent.name}
                  title={agent.title}
                  description={agent.description}
                  toolsCount={agent.toolsCount}
                />
              ))
            : skeletons.map((i) => <AgentCardSkeleton key={i} />)}
        </div>
      </div>
    </section>
  );
}
