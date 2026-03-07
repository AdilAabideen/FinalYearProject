import { useEffect, useMemo, useRef, useState } from 'react';
import { agentDiscoveryService } from '../services/agentDiscoveryService';
import type { AgentCatalogDetail, AgentCatalogSummary } from '../types/agents';
import { AgentCard, AgentCardSkeleton } from '../components/AgentCard';
import { AgentDetailSplitView } from '../components/agent/AgentDetailSplitView';

type AgentsLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; agents: AgentCatalogSummary[] };

type HeaderOverride = { title: string; subtitle?: string; showSearch?: boolean };

type AgentsPageProps = {
  onHeaderChange?: (override: HeaderOverride | null) => void;
};

type AgentDetailState =
  | { status: 'closed' }
  | { status: 'loading'; agentName: string }
  | { status: 'error'; agentName: string; message: string }
  | { status: 'success'; agent: AgentCatalogDetail };

export function AgentsPage({ onHeaderChange }: AgentsPageProps) {
  const [state, setState] = useState<AgentsLoadState>({ status: 'loading' });
  const [detail, setDetail] = useState<AgentDetailState>({ status: 'closed' });
  const detailAbortRef = useRef<AbortController | null>(null);

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

  useEffect(() => {
    return () => {
      detailAbortRef.current?.abort();
    };
  }, []);

  const skeletons = useMemo(() => Array.from({ length: 6 }, (_, i) => i), []);

  function closeDetail() {
    detailAbortRef.current?.abort();
    detailAbortRef.current = null;
    setDetail({ status: 'closed' });
    onHeaderChange?.(null);
  }

  async function openAgent(agentName: string) {
    const summary =
      state.status === 'success' ? state.agents.find((a) => a.name === agentName) : undefined;

    onHeaderChange?.({
      title: summary?.title ?? agentName,
      subtitle: summary?.description,
      showSearch: false,
    });

    detailAbortRef.current?.abort();
    const ac = new AbortController();
    detailAbortRef.current = ac;
    setDetail({ status: 'loading', agentName });

    try {
      const agent = await agentDiscoveryService.getAgent(agentName, ac.signal);
      if (ac.signal.aborted) return;
      setDetail({ status: 'success', agent });
      onHeaderChange?.({ title: agent.title, subtitle: agent.description, showSearch: false });
    } catch (e: unknown) {
      if (ac.signal.aborted) return;
      setDetail({
        status: 'error',
        agentName,
        message: e instanceof Error ? e.message : 'Failed to load agent',
      });
    }
  }

  if (detail.status !== 'closed') {
    return (
      <section aria-label="Agent Details">
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={closeDetail}
              className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-50"
            >
              Back to agents
            </button>
          </div>

          {detail.status === 'loading' ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="h-5 w-40 animate-pulse rounded bg-slate-200" />
                <div className="mt-4 aspect-square w-full animate-pulse rounded-2xl bg-slate-100" />
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="h-5 w-48 animate-pulse rounded bg-slate-200" />
                <div className="mt-4 space-y-3">
                  <div className="h-24 animate-pulse rounded-2xl bg-slate-100" />
                  <div className="h-24 animate-pulse rounded-2xl bg-slate-100" />
                  <div className="h-24 animate-pulse rounded-2xl bg-slate-100" />
                </div>
              </div>
            </div>
          ) : null}

          {detail.status === 'error' ? (
            <div className="space-y-4">
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                {detail.message}
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => openAgent(detail.agentName)}
                  className="inline-flex items-center rounded-xl bg-PrimaryBlue px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-PrimaryBlue/90"
                >
                  Retry
                </button>
                <button
                  type="button"
                  onClick={closeDetail}
                  className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-50"
                >
                  Back
                </button>
              </div>
            </div>
          ) : null}

          {detail.status === 'success' ? <AgentDetailSplitView agent={detail.agent} /> : null}
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Agents">
      <div className="space-y-6">
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
                  onOpen={openAgent}
                />
              ))
            : skeletons.map((i) => <AgentCardSkeleton key={i} />)}
        </div>
      </div>
    </section>
  );
}
