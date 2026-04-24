import type { MasWorkflowSummary } from '../../../types/mas';

type MasDetailSplitViewProps = {
  workflow: MasWorkflowSummary;
};

export function MasDetailSplitView({ workflow }: MasDetailSplitViewProps) {
  return (
    <div className="grid h-full min-h-0 p-0 lg:grid-cols-1">
      <section className="flex min-h-0 flex-col border-r border-slate-200 [background-image:radial-gradient(circle_at_1px_1px,rgba(148,163,184,0.35)_1px,transparent_0)] [background-size:18px_18px] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-slate-900">MAS Workflow Topology</h2>
          <div className="flex flex-row items-center gap-6">
            <p className="text-xs text-slate-500"> MAS detail view</p>
            <p className="text-xs text-slate-500"> Click Each Agent to Inspect and Test in Detail</p>
          </div>

        </div>

      </section>


    </div>
  );
}
