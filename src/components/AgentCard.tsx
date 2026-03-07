import arrowRightIcon from '../assets/figma/icon-arrow-right.png';

type AgentCardProps = {
  title: string;
  toolsCount: number;
  testCasesCount: number;
};

export function AgentCard({ title, toolsCount, testCasesCount }: AgentCardProps) {
  return (
    <div className="flex w-full max-w-sm flex-col justify-between rounded-2xl border-2 border-neutral-200 bg-neutral-100 p-4 shadow-sm">
      <div>
        <h2 className="text-xl font-medium">{title}</h2>
        <div className="mt-1 text-sm font-light text-neutral-700">
          <p>Tools - {toolsCount}</p>
          <p>Test Cases - {testCasesCount}</p>
        </div>
      </div>
      <button
        type="button"
        className="ml-auto mt-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white shadow-sm ring-1 ring-neutral-200 transition hover:bg-neutral-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-black/20"
        aria-label={`Open ${title}`}
      >
        <img alt="" src={arrowRightIcon} className="h-5 w-5 object-contain" draggable={false} />
      </button>
    </div>
  );
}
