import { useId, useState } from 'react';
import { formatJson } from '../../lib/formatJson';
import type { AgentCatalogDetail } from '../../types/agents';
import { AgentInputForm } from './AgentInputForm';
import { CodeBlock } from '../ui/CodeBlock';
import { SegmentedTabs } from '../ui/SegmentedTabs';

type OutputTabKey = 'traces' | 'results';

const outputTabs: Array<{ key: OutputTabKey; label: string }> = [
  { key: 'traces', label: 'Agent Traces' },
  { key: 'results', label: 'Results' },
];

type RunAgentTabProps = {
  agent: AgentCatalogDetail;
};

export default function RunAgentTab({ agent }: RunAgentTabProps) {
  const outputTabsId = useId();
  const [view, setView] = useState<'input' | 'output'>('input');
  const [activeOutputTab, setActiveOutputTab] = useState<OutputTabKey>('traces');
  const [value, setValue] = useState<Record<string, unknown>>({});
  const [lastRunInput, setLastRunInput] = useState<Record<string, unknown> | null>(null);

  function handleRun() {
    console.log('Agent input:', value);
    setLastRunInput(value);
    setView('output');
    setActiveOutputTab('traces');
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 pt-2 h-full">
      <div>
        {view === 'input' && <p className="mt-1 text-md text-slate-600">
          Select tools and provide inputs to run this agent.
        </p>}
      </div>

      {view === 'input' ? (
        <>
          <div className="mt-4">
            <AgentInputForm schema={agent.inputSchema} value={value} onChange={setValue} />
          </div>

          <div className="mt-6 flex items-center justify-end">
            <button
              type="button"
              onClick={handleRun}
              className="inline-flex items-center justify-center rounded-xl bg-PrimaryBlue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-PrimaryBlue/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
            >
              Run Agent
            </button>
          </div>
        </>
      ) : (
        <div className="mt-2 ">
          <SegmentedTabs
            idBase={outputTabsId}
            tabs={outputTabs}
            value={activeOutputTab}
            onChange={setActiveOutputTab}
            ariaLabel="Run output views"
          />

          <div className="mt-4 h-full">
            <div
              id={`${outputTabsId}-panel-traces`}
              role="tabpanel"
              aria-labelledby={`${outputTabsId}-tab-traces`}
              hidden={activeOutputTab !== 'traces'}
              className="h-full"
            >
              <div className="rounded-2xl border border-slate-200 bg-white p-4 h-full">
                <h4 className="text-sm font-semibold text-slate-900">Agent Traces</h4>
                <p className="mt-1 text-sm text-slate-600">
                  Traces will appear here once the run endpoint is connected.
                </p>
              </div>
            </div>

            <div
              id={`${outputTabsId}-panel-results`}
              role="tabpanel"
              aria-labelledby={`${outputTabsId}-tab-results`}
              hidden={activeOutputTab !== 'results'}
              className="h-full"
            >
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <h4 className="text-sm font-semibold text-slate-900">Results</h4>
                <p className="mt-1 text-sm text-slate-600">
                  Results will appear here once the run endpoint is connected.
                </p>
                {lastRunInput ? (
                  <CodeBlock code={formatJson(lastRunInput)} className="mt-3 max-h-80" />
                ) : null}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
