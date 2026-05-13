import { useMemo, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { ActiveHandoffEdges, AgentRunningStatus, BoundaryEdgeHighlights } from './MasDetailSplitView';
import { formatMasAgentName } from '../utils/format';
import {
  type MetricsState,
  normalizeOutputValue,
} from '../utils/masTraces';
import { MasTracesAgentPanel, type TraceTab } from './MasTracesAgentPanel';
import { MasTracesGeneralPanel } from './MasTracesGeneralPanel';
import { useMasAgentMetricsStore } from '../hooks/useMasAgentMetricsStore';
import { useMasSwarmStream } from '../hooks/useMasSwarmStream';

type MasTracesTabProps = {
  agentNames: string[];
  eventsStreamUrl: string;
  swarm_run_id: string;
  setAgentStatus: Dispatch<SetStateAction<AgentRunningStatus>>;
  setActiveHandoffEdges: Dispatch<SetStateAction<ActiveHandoffEdges>>;
  setBoundaryEdgeHighlights: Dispatch<SetStateAction<BoundaryEdgeHighlights>>;
  onMasDone: () => Promise<void>;
};

const tabs: TraceTab[] = [
  {
    key: 'traces',
    label: 'Traces',
  },
  {
    key: 'output',
    label: 'Output',
  },
  {
    key: 'metrics',
    label: 'Metrics',
  },
];

// Renders the MAS traces tab.
export default function MasTracesTab({
  agentNames,
  eventsStreamUrl,
  swarm_run_id,
  setAgentStatus,
  setActiveHandoffEdges,
  setBoundaryEdgeHighlights,
  onMasDone,
}: MasTracesTabProps) {
  const normalizedAgentNames = useMemo(
    () => agentNames.filter((name, index, arr) => arr.indexOf(name) === index),
    [agentNames],
  );

  const [activeAgentName, setActiveAgentName] = useState<string>('general');

  const { agentMetricsStates, getAgentMetrics, resetAgentMetricsStates, idleMetricsState } =
    useMasAgentMetricsStore();
  const { agentRunIds, agentOutputs, streamState, errorText, generalEvents } = useMasSwarmStream({
    agentNames: normalizedAgentNames,
    eventsStreamUrl,
    onMasDone,
    setAgentStatus,
    setActiveHandoffEdges,
    setBoundaryEdgeHighlights,
    getAgentMetrics,
    resetAgentMetricsStates,
  });
  const activeAgentRunId =
    activeAgentName && activeAgentName !== 'general' ? agentRunIds[activeAgentName] ?? null : null;
  const activeAgentOutput =
    activeAgentName && activeAgentName !== 'general' ? agentOutputs[activeAgentName] ?? null : null;
  const activeMetricsState: MetricsState =
    activeAgentName && activeAgentName !== 'general'
      ? agentMetricsStates[activeAgentName] ?? idleMetricsState
      : idleMetricsState;

  const [selectedTab, setSelectedTab] = useState<TraceTab>(tabs[0]);
  



  return (
    <div className="grid h-full w-full grid-cols-5 grid-rows-1">
      <div className="col-span-1 h-full border-r border-slate-300 bg-slate-100/60">
        <button
          type="button"
          onClick={() => setActiveAgentName("general")}
          className={[
            'w-full border-b border-slate-300 p-3 text-left text-sm transition-all duration-150 ease-in-out',
            activeAgentName === "general"
              ? 'bg-white font-semibold text-slate-900'
              : 'text-slate-700 hover:bg-slate-50 hover:pl-4 hover:text-slate-900',
          ].join(' ')}
        >
          General
        </button>
        {normalizedAgentNames.map((agentName) => {
          const active = activeAgentName === agentName;

          return (
            <button
              key={agentName}
              type="button"
              onClick={() => setActiveAgentName(agentName)}
              className={[
                'w-full border-b border-slate-300 p-3 text-left text-sm transition-all duration-150 ease-in-out',
                active
                  ? 'bg-white font-semibold text-slate-900'
                  : 'text-slate-700 hover:bg-slate-50 hover:pl-4 hover:text-slate-900',
              ].join(' ')}
            >
              {formatMasAgentName(agentName)}
            </button>
          );
        })}
      </div>

      <div className="col-span-4 flex h-full min-h-0 w-full flex-col bg-white">
        {errorText ? (
          <div className="border-b border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
            {errorText}
          </div>
        ) : null}
        {activeAgentName === 'general' ? (
          <MasTracesGeneralPanel
            swarmRunId={swarm_run_id}
            streamState={streamState}
            generalEvents={generalEvents}
            agentCount={normalizedAgentNames.length}
          />
        ) :
          <MasTracesAgentPanel
            activeAgentName={activeAgentName}
            activeAgentRunId={activeAgentRunId}
            activeAgentOutput={activeAgentOutput}
            activeMetricsState={activeMetricsState}
            selectedTab={selectedTab}
            setSelectedTab={setSelectedTab}
            tabs={tabs}
            normalizeOutputValue={normalizeOutputValue}
          />
        }
      </div>
    </div>
  );
}
