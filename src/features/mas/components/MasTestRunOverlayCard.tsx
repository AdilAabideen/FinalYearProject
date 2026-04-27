type MasTestRunOverlayCardProps = {
  selectedCount: number;
  ranCount: number;
  toRunCount: number;
  passedCount: number;
  failedCount: number;
  masTestRunId: string | null;
  startingTests: boolean;
  onStartTests: () => void;
};

export function MasTestRunOverlayCard({
  selectedCount,
  ranCount,
  toRunCount,
  passedCount,
  failedCount,
  masTestRunId,
  startingTests,
  onStartTests,
}: MasTestRunOverlayCardProps) {
  return (
    <div className="absolute bottom-3 left-3 z-10">
      <div className="flex items-end gap-3 rounded-lg border border-slate-200 bg-white/95 px-3 py-2 backdrop-blur">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            Start Test Cases
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="font-semibold text-slate-900">
              {selectedCount} {selectedCount === 1 ? 'test' : 'tests'}
            </span>
            <span>•</span>
            <span>{ranCount} ran</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <div className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1">
              <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-500">To Run</p>
              <p className="text-[11px] font-semibold text-slate-900">{toRunCount}</p>
            </div>
            <div
              className={[
                'rounded-md border border-slate-200 px-2 py-1',
                passedCount === 0 ? 'bg-slate-50' : 'bg-green-100',
              ].join(' ')}
            >
              <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-500">Passed</p>
              <p className="text-[11px] font-semibold text-slate-900">{passedCount}</p>
            </div>
            <div
              className={[
                'rounded-md border border-slate-200 px-2 py-1',
                failedCount === 0 ? 'bg-slate-50' : 'bg-red-100',
              ].join(' ')}
            >
              <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-500">Failed</p>
              <p className="text-[11px] font-semibold text-slate-900">{failedCount}</p>
            </div>
          </div>
          {masTestRunId ? (
            <p className="mt-1 truncate text-[10px] text-slate-500">Run: {masTestRunId}</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={onStartTests}
          disabled={selectedCount === 0 || startingTests}
          className={[
            'inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-sm font-semibold transition',
            selectedCount === 0 || startingTests
              ? 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400'
              : 'cursor-pointer border-PrimaryBlue/20 bg-PrimaryBlue text-white hover:bg-PrimaryBlue/90',
          ].join(' ')}
        >
          {startingTests ? 'Starting…' : 'Start Tests'}
        </button>
      </div>
    </div>
  );
}
