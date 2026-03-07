import arrowRightIcon from '../assets/figma/icon-arrow-right.png';

type AgentCardProps = {
  title: string;
  toolsCount: number;
  testCasesCount: number;
};

export function AgentCard({ title, toolsCount, testCasesCount }: AgentCardProps) {
  return (
    <div className="group flex w-full max-w-sm flex-col rounded-2xl border border-slate-200 border-t-4 border-t-teal-600 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
        <span className="inline-flex items-center rounded-full bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700 ring-1 ring-teal-100">
          Ready
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <div className="inline-flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-200/60">
          <span className="font-semibold text-slate-900">{toolsCount}</span>
          <span className="text-slate-500">Tools</span>
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-200/60">
          <span className="font-semibold text-slate-900">{testCasesCount}</span>
          <span className="text-slate-500">Test Cases</span>
        </div>
      </div>

      <button
        type="button"
        className="ml-auto mt-6 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white shadow-sm transition hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        aria-label={`Open ${title}`}
      >
        <img
          alt=""
          src={arrowRightIcon}
          className="h-5 w-5 object-contain invert transition-transform group-hover:translate-x-0.5"
          draggable={false}
        />
      </button>
    </div>
  );
}
