import type { MasWorkflowSummary } from '../../../types/mas';
import { MasDiagram } from './MasDiagram';

type MasDetailSplitViewProps = {
  workflow: MasWorkflowSummary;
};

export function MasDetailSplitView({ workflow }: MasDetailSplitViewProps) {
  return (
    <div className="grid h-full min-h-0 p-0 lg:grid-cols-1">
      <section className="flex min-h-0 flex-col border-r border-slate-200 p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">MAS Workflow Topology</h2>

          </div>
          <div className="text-right">
            <p className="text-xs font-semibold text-slate-900">{workflow.name}</p>
          </div>
        </div>

        <div className="mt-2 min-h-[560px] flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <MasDiagram workflowName={workflow.name} />
        </div>
      </section>
    </div>
  );
}
