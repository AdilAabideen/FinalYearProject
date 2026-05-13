import type { Dispatch, SetStateAction } from 'react';
import type { MasTestCaseRead } from '../../../types/masTests';
import type { ActiveHandoffEdges, AgentRunningStatus, BoundaryEdgeHighlights } from './MasDetailSplitView';
import MasTracesTab from './MasTracesTab';

type TraceRun = {
  swarmRunId: string;
  eventsStreamUrl: string;
};

type MasTestCaseTracesPanelProps = {
  testCase: MasTestCaseRead | null;
  traceRun: TraceRun | null;
  agentNames: string[];
  setAgentStatus: Dispatch<SetStateAction<AgentRunningStatus>>;
  setActiveHandoffEdges: Dispatch<SetStateAction<ActiveHandoffEdges>>;
  setBoundaryEdgeHighlights: Dispatch<SetStateAction<BoundaryEdgeHighlights>>;
  onMasDone: () => Promise<void>;
};

// Renders the MAS test case traces.
export function MasTestCaseTracesPanel({
  testCase,
  traceRun,
  agentNames,
  setAgentStatus,
  setActiveHandoffEdges,
  setBoundaryEdgeHighlights,
  onMasDone,
}: MasTestCaseTracesPanelProps) {
  if (!testCase) {
    return (
      <div className="p-4">
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
          <p className="text-sm font-semibold text-slate-900">No test case selected.</p>
        </div>
      </div>
    );
  }

  if (!traceRun) {
    return (
      <div className="p-4">
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
          <p className="text-sm font-semibold text-slate-900">No trace stream yet</p>
          <p className="mt-2 text-sm text-slate-500">
            Start tests and bind the selected case to a MAS run stream to view traces here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 overflow-hidden p-0">
      <MasTracesTab
        agentNames={agentNames}
        eventsStreamUrl={traceRun.eventsStreamUrl}
        swarm_run_id={traceRun.swarmRunId}
        setAgentStatus={setAgentStatus}
        setActiveHandoffEdges={setActiveHandoffEdges}
        setBoundaryEdgeHighlights={setBoundaryEdgeHighlights}
        onMasDone={onMasDone}
      />
    </div>
  );
}
