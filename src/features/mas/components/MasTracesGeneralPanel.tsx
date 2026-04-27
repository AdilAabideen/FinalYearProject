import { formatTraceTimestamp, type MasGeneralEvent } from '../utils/masTraces';

type MasTracesGeneralPanelProps = {
  swarmRunId: string;
  streamState: string;
  generalEvents: MasGeneralEvent[];
  agentCount: number;
};

export function MasTracesGeneralPanel({
  swarmRunId,
  streamState,
  generalEvents,
  agentCount,
}: MasTracesGeneralPanelProps) {
  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-white">
      <div className="flex w-full shrink-0 flex-col gap-3 border-b border-slate-200 px-5 py-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-1">
            <p className="text-xl font-semibold text-slate-900">General Traces</p>
            <p className="text-xs font-semibold text-slate-600">
              Run ID : <span className="font-mono text-slate-700">{swarmRunId}</span>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            Stream: {streamState}
          </div>
          <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
            Events: {generalEvents.length}
          </div>
          <div className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            Agents: {agentCount}
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 w-full overflow-y-auto px-5 py-4 pb-20">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 py-1">
          {generalEvents.length ? (
            generalEvents.map((event, index) => (
              <div key={`${event.created_at}-${event.event_type}-${index}`} className="space-y-1">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">SWARM EVENT</p>
                  <p className="text-[11px] font-mono text-slate-400">
                    {formatTraceTimestamp(event.created_at)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-slate-900">{event.event_type}</p>
                  <span className="text-xs text-slate-400">•</span>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {event.arch_type}
                  </p>
                </div>
                <p className="max-w-3xl text-sm text-slate-700">{event.description}</p>
              </div>
            ))
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="text-sm font-semibold text-slate-900">Waiting for swarm events</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
