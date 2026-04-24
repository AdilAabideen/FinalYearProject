import { useState, useEffect, useRef, useMemo } from 'react';
import type { MasWorkflowSummary } from '../../../types/mas';
import { masDiscoveryService } from '../../../services/masDiscoveryService';
import { AgentCard, AgentCardSkeleton } from '../../agents/components/AgentCard';
import { MasCard } from '../../agents/components/MasCard';

type MasLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; mas: MasWorkflowSummary[] };

export function MasPage() {

  const [state, setState] = useState<MasLoadState>({ status: 'loading' })
  const detailAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const ac = new AbortController();

    async function loadAgents() {
      try {
        const data = await masDiscoveryService.listMas(ac.signal);
        if (!ac.signal.aborted) {
          setState({ status: 'success', mas: data });
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

  useEffect(() => {
    return () => {
      detailAbortRef.current?.abort();
    };
  }, []);

  return (
    <section aria-label="Multi Agent Systems" className="h-full">
      <div className="space-y-6">
        {state.status === 'error' ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {state.message}
          </div>
        ) : null}

        <div className="grid items-start gap-8 sm:grid-cols-2 lg:grid-cols-3 p-6">
          {state.status === 'success'
            ? state.mas.map((mas) => (
              <MasCard
                workflowId={mas.workflowId}
                name={mas.name}
                version={mas.version}
                description={mas.description}
                participatingAgentsCount={mas.participatingAgentsCount}
                startAgentsCount={mas.startAgentsCount}
                finalizingAgentsCount={mas.finalizingAgentsCount}
                gatesCount={mas.gatesCount}
                sourcesCount={mas.sourcesCount}
              />
            ))
            : skeletons.map((i) => <AgentCardSkeleton key={i} />)}
        </div>
      </div>
    </section>
  );
}
