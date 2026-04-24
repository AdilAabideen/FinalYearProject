import { useEffect, useMemo, useRef, useState } from 'react';
import type { MasWorkflowSummary } from '../../../types/mas';
import { masDiscoveryService } from '../../../services/masDiscoveryService';
import { MasCard, MasCardSkeleton } from '../../agents/components/MasCard';
import { MasDetailSplitView } from '../components/MasDetailSplitView';

type MasLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; mas: MasWorkflowSummary[] };

type BackAction = { label?: string; onClick: () => void };
type HeaderOverride = {
  title: string;
  subtitle?: string;
  showSearch?: boolean;
  backAction?: BackAction;
  contentOverflow?: 'auto' | 'hidden';
};

type MasPageProps = {
  onHeaderChange?: (override: HeaderOverride | null) => void;
};

type MasDetailState =
  | { status: 'closed' }
  | { status: 'loading'; workflowId: string }
  | { status: 'success'; workflow: MasWorkflowSummary };

export function MasPage({ onHeaderChange }: MasPageProps) {
  const [state, setState] = useState<MasLoadState>({ status: 'loading' });
  const [detail, setDetail] = useState<MasDetailState>({ status: 'closed' });
  const detailAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const ac = new AbortController();

    async function loadMas() {
      try {
        const data = await masDiscoveryService.listMas(ac.signal);
        if (!ac.signal.aborted) {
          setState({ status: 'success', mas: data });
        }
      } catch (e: unknown) {
        if (ac.signal.aborted) return;
        setState({
          status: 'error',
          message: e instanceof Error ? e.message : 'Failed to load workflows',
        });
      }
    }

    loadMas();

    return () => ac.abort();
  }, []);

  const skeletons = useMemo(() => Array.from({ length: 6 }, (_, i) => i), []);

  useEffect(() => {
    return () => {
      detailAbortRef.current?.abort();
    };
  }, []);

  function closeDetail() {
    detailAbortRef.current?.abort();
    detailAbortRef.current = null;
    setDetail({ status: 'closed' });
    onHeaderChange?.(null);
  }

  async function openWorkflow(workflowId: string) {
    const summary =
      state.status === 'success'
        ? state.mas.find((workflow) => workflow.workflowId === workflowId)
        : undefined;

    onHeaderChange?.({
      title: summary?.name ?? workflowId,
      subtitle: summary?.description,
      showSearch: false,
      backAction: { label: 'Back to workflows', onClick: closeDetail },
      contentOverflow: 'hidden',
    });

    detailAbortRef.current?.abort();
    const ac = new AbortController();
    detailAbortRef.current = ac;
    setDetail({ status: 'loading', workflowId });

    window.setTimeout(() => {
      if (ac.signal.aborted) return;
      if (!summary) {
        closeDetail();
        return;
      }

      setDetail({ status: 'success', workflow: summary });
      onHeaderChange?.({
        title: summary.name,
        subtitle: summary.description,
        showSearch: false,
        backAction: { label: 'Back to workflows', onClick: closeDetail },
        contentOverflow: 'hidden',
      });
    }, 180);
  }

  if (detail.status !== 'closed') {
    return (
      <section aria-label="Workflow Details" className="h-full">
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

          {detail.status === 'success' ? (
            <div className="flex-1 min-h-0">
              <MasDetailSplitView workflow={detail.workflow} />
            </div>
          ) : null}
        </div>
      </section>
    );
  }

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
                key={mas.workflowId}
                workflowId={mas.workflowId}
                name={mas.name}
                version={mas.version}
                description={mas.description}
                participatingAgentsCount={mas.participatingAgentsCount}
                startAgentsCount={mas.startAgentsCount}
                finalizingAgentsCount={mas.finalizingAgentsCount}
                gatesCount={mas.gatesCount}
                sourcesCount={mas.sourcesCount}
                onOpen={openWorkflow}
              />
            ))
            : skeletons.map((i) => <MasCardSkeleton key={i} />)}
        </div>
      </div>
    </section>
  );
}
