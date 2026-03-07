import type { AgentCatalogDetail } from '../../types/agents';
import { AgentDiagram } from './AgentDiagram';
import { AgentSchemasPanel } from './AgentSchemasPanel';

type AgentDetailSplitViewProps = {
  agent: AgentCatalogDetail;
};

export function AgentDetailSplitView({ agent }: AgentDetailSplitViewProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-slate-900">Agent Diagram</h2>
          <p className="text-xs text-slate-500">Hover a tool to preview its schema</p>
        </div>
        <div className="mt-4 aspect-square w-full">
          <AgentDiagram agent={agent} />
        </div>
      </section>

      <section className="min-h-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <AgentSchemasPanel agent={agent} />
      </section>
    </div>
  );
}

