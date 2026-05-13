import { useEffect, useMemo, useRef, useState } from 'react';
import { agentDiscoveryService } from '../../../services/agentDiscoveryService';
import type { AgentCatalogDetail, AgentCatalogSummary } from '../../../types/agents';
import { AgentCard, AgentCardSkeleton } from '../components/AgentCard';
import { AgentDetailSplitView } from '../components/AgentDetailSplitView';

export type AgentsLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; agents: AgentCatalogSummary[] };

export type BackAction = { label?: string; onClick: () => void };
export type HeaderOverride = {
  title: string;
  subtitle?: string;
  showSearch?: boolean;
  backAction?: BackAction;
  contentOverflow?: 'auto' | 'hidden';
};

type AgentsPageProps = {
  onHeaderChange?: (override: HeaderOverride | null) => void;
};

export type AgentDetailState =
  | { status: 'closed' }
  | { status: 'loading'; agentName: string }
  | { status: 'error'; agentName: string; message: string }
  | { status: 'success'; agent: AgentCatalogDetail };

// Renders the agents page.
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

// Closes detail.
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
      backAction: { label: 'Back to agents', onClick: closeDetail },
      contentOverflow: 'hidden',
    });

    detailAbortRef.current?.abort();
    const ac = new AbortController();
    detailAbortRef.current = ac;
    setDetail({ status: 'loading', agentName });

    try {
      const agent = await agentDiscoveryService.getAgent(agentName, ac.signal);
      if (ac.signal.aborted) return;
      setDetail({ status: 'success', agent });
      onHeaderChange?.({
        title: agent.title,
        subtitle: agent.description,
        showSearch: false,
        backAction: { label: 'Back to agents', onClick: closeDetail },
        contentOverflow: 'hidden',
      });
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
      <section aria-label="Agent Details" className="h-full">
        <div className="flex h-full flex-col">
          {detail.status === 'loading' ? (
            <div className="grid flex-1 gap-6 p-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="h-5 w-40 animate-pulse rounded bg-slate-200" />
                <div className="mt-4 h-full w-full animate-pulse rounded-2xl bg-slate-100" />
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
            <div className="space-y-4 p-6">
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
              </div>
            </div>
          ) : null}

          {detail.status === 'success' ? (
            <div className="flex-1 min-h-0">
              <AgentDetailSplitView agent={detail.agent} />
            </div>
          ) : null}
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

        <div className="grid items-start gap-8 sm:grid-cols-2 lg:grid-cols-3 p-6">
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
