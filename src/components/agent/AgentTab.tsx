import { useId, useState } from 'react';
import type { AgentCatalogDetail } from '../../types/agents';
import { SegmentedTabs } from '../ui/SegmentedTabs';
import RunAgentTab from './RunAgentTab';
import PreviousRuns from './PreviousRuns';

type TabKey = 'run' | 'previous' | 'tests';

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: 'run', label: 'Run Agent' },
  { key: 'previous', label: 'Previous Runs' },
  { key: 'tests', label: 'Test Cases' },
];

type AgentTabProps = {
  agent: AgentCatalogDetail;
};

export default function AgentTab({ agent }: AgentTabProps) {
  const baseId = useId();
  const [activeTab, setActiveTab] = useState<TabKey>('run');

  function tabId(key: TabKey) {
    return `${baseId}-tab-${key}`;
  }

  function panelId(key: TabKey) {
    return `${baseId}-panel-${key}`;
  }

  return (
    <div className="flex h-full min-h-0 flex-col rounded-none">
      <SegmentedTabs
        idBase={baseId}
        tabs={tabs}
        value={activeTab}
        onChange={setActiveTab}
        ariaLabel="Agent views"
      />

      <div className="mt-4 flex-1 min-h-0 overflow-hidden">
        <div
          id={panelId('run')}
          role="tabpanel"
          aria-labelledby={tabId('run')}
          hidden={activeTab !== 'run'}
          className="h-full overflow-auto"
        >
          <RunAgentTab key={agent.name} agent={agent} />
        </div>

        <div
          id={panelId('previous')}
          role="tabpanel"
          aria-labelledby={tabId('previous')}
          hidden={activeTab !== 'previous'}
          className="h-full overflow-auto"
        >
          <PreviousRuns agentName={agent.name} />
        </div>

        <div
          id={panelId('tests')}
          role="tabpanel"
          aria-labelledby={tabId('tests')}
          hidden={activeTab !== 'tests'}
          className="h-full overflow-auto"
        >
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">Test Cases</h3>
            <p className="mt-1 text-sm text-slate-600">Create and run repeatable test cases for this agent.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
