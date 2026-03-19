import type { AgentCatalogDetail } from '../../../types/agents';
import { AgentDiagram } from './AgentDiagram';
import AgentTab from './AgentTab';

type AgentDetailSplitViewProps = {
  agent: AgentCatalogDetail;
};

export function AgentDetailSplitView({ agent }: AgentDetailSplitViewProps) {
  return (
    <div className="grid h-full min-h-0 p-0 lg:grid-cols-2">
      <section className="flex min-h-0 flex-col border-r border-slate-200 [background-image:radial-gradient(circle_at_1px_1px,rgba(148,163,184,0.35)_1px,transparent_0)] [background-size:18px_18px] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-slate-900">Agent Diagram</h2>
          <p className="text-xs text-slate-500">Hover a tool to preview its schema</p>
        </div>
        <div className="mt-4 flex-1 min-h-0 w-full">
          <AgentDiagram agent={agent} />
        </div>
      </section>

      <section className="min-h-0   bg-white p-4 shadow-sm">
        <AgentTab agent={agent} />
      </section>
    </div>
  );
}
