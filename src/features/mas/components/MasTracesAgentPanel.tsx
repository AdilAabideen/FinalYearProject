import type { Dispatch, SetStateAction } from 'react';
import { AgentTracesComponent } from '../../agents/components/AgentTracesComponent';
import JsonRenderer from './JsonRenderer';
import { MasTabs } from './MasTabs';
import { formatMasAgentName } from '../utils/format';
import { MasTracesMetricsPanel, type MetricsState } from './MasTracesMetricsPanel';

export type TraceTabKey = 'traces' | 'output' | 'metrics';

export type TraceTab = {
  key: TraceTabKey;
  label: string;
};

type MasTracesAgentPanelProps = {
  activeAgentName: string;
  activeAgentRunId: string | null;
  activeAgentOutput: unknown;
  activeMetricsState: MetricsState;
  selectedTab: TraceTab;
  setSelectedTab: Dispatch<SetStateAction<TraceTab>>;
  tabs: TraceTab[];
  normalizeOutputValue: (value: unknown) => unknown;
};

export function MasTracesAgentPanel({
  activeAgentName,
  activeAgentRunId,
  activeAgentOutput,
  activeMetricsState,
  selectedTab,
  setSelectedTab,
  tabs,
  normalizeOutputValue,
}: MasTracesAgentPanelProps) {
  const normalizedOutput = normalizeOutputValue(activeAgentOutput);

  function viewerTabId(key: TraceTabKey) {
    return `${activeAgentName}-${key}-tab`;
  }

  function viewerPanelId(key: TraceTabKey) {
    return `${activeAgentName}-${key}-panel`;
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-white">
      <div className="shrink-0 border-b border-slate-200 px-4 py-3">
        <p className="text-base font-semibold text-slate-900">{formatMasAgentName(activeAgentName)}</p>
        <p className="mt-1 text-xs font-medium text-slate-500">{activeAgentName}</p>
      </div>

      <MasTabs
        tabs={tabs}
        activeKey={selectedTab.key}
        onChange={(key) => {
          const nextTab = tabs.find((tab) => tab.key === key);
          if (nextTab) setSelectedTab(nextTab);
        }}
        wrapperClassName="w-full border-b border-slate-200"
        buttonClassName="cursor-pointer border-r border-slate-200 px-3 py-2 text-sm font-medium transition-colors"
        minTabWidthClassName="min-w-0"
        activeButtonClassName="bg-slate-100 text-slate-900"
        inactiveButtonClassName="bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900"
        labelClassName=""
        activeLabelClassName=""
        inactiveLabelClassName=""
      />

      <div className="min-h-0 flex-1 overflow-hidden">
        {selectedTab.key === 'traces' ? (
          activeAgentRunId ? (
            <div
              id={viewerPanelId('traces')}
              role="tabpanel"
              aria-labelledby={viewerTabId('traces')}
              className="h-full min-h-0 overflow-hidden p-3 pb-20"
            >
              <AgentTracesComponent runId={activeAgentRunId} />
            </div>
          ) : (
            <div className="flex h-full items-start justify-start p-6">
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
                <p className="text-sm font-semibold text-slate-900">Waiting for agent run</p>
                <p className="mt-2 text-sm text-slate-500">
                  Trace output will appear here once this agent starts running.
                </p>
              </div>
            </div>
          )
        ) : selectedTab.key === 'metrics' ? (
          <div
            id={viewerPanelId('metrics')}
            role="tabpanel"
            aria-labelledby={viewerTabId('metrics')}
            className="h-full min-h-0 overflow-auto pb-20"
          >
            <MasTracesMetricsPanel activeMetricsState={activeMetricsState} />
          </div>
        ) : normalizedOutput ? (
          <div className="h-full min-h-0 overflow-y-auto pb-20">
            <div className="space-y-2">
              <JsonRenderer title="Agent Communication Output" value={normalizedOutput} />
            </div>
          </div>
        ) : (
          <div className="flex h-full items-start justify-start p-6">
            <div className="w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
              <p className="text-sm font-semibold text-slate-900">No Agent Communication</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
