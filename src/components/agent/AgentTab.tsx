import { useId, useRef, useState } from 'react';
import { cn } from '../../lib/cn';
import RunAgentTab from './RunAgentTab';

type TabKey = 'run' | 'previous' | 'tests';

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: 'run', label: 'Run Agent' },
  { key: 'previous', label: 'Previous Runs' },
  { key: 'tests', label: 'Test Cases' },
];

export default function AgentTab() {
  const baseId = useId();
  const [activeTab, setActiveTab] = useState<TabKey>('run');
  const tabRefs = useRef<Record<TabKey, HTMLButtonElement | null>>({
    run: null,
    previous: null,
    tests: null,
  });

  function tabId(key: TabKey) {
    return `${baseId}-tab-${key}`;
  }

  function panelId(key: TabKey) {
    return `${baseId}-panel-${key}`;
  }

  function handleTabKeyDown(key: TabKey) {
    return (e: React.KeyboardEvent<HTMLButtonElement>) => {
      const currentIndex = tabs.findIndex((tab) => tab.key === key);
      if (currentIndex < 0) return;

      let nextIndex = currentIndex;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nextIndex = (currentIndex + 1) % tabs.length;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      if (e.key === 'Home') nextIndex = 0;
      if (e.key === 'End') nextIndex = tabs.length - 1;

      if (nextIndex === currentIndex) return;

      e.preventDefault();
      const nextKey = tabs[nextIndex]?.key ?? 'run';
      setActiveTab(nextKey);
      tabRefs.current[nextKey]?.focus();
    };
  }

  return (
    <div className="flex h-full min-h-0 flex-col rounded-none">
      <div
        role="tablist"
        aria-label="Agent views"
        className="grid grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1 ring-1 ring-slate-200"
      >
        {tabs.map((tab) => {
          const selected = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              ref={(node) => {
                tabRefs.current[tab.key] = node;
              }}
              id={tabId(tab.key)}
              role="tab"
              type="button"
              tabIndex={selected ? 0 : -1}
              aria-selected={selected}
              aria-controls={panelId(tab.key)}
              onClick={() => setActiveTab(tab.key)}
              onKeyDown={handleTabKeyDown(tab.key)}
              className={cn(
                'inline-flex items-center justify-center rounded-lg px-3 py-2 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white',
                selected
                  ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200'
                  : 'text-slate-600 hover:bg-white/70 hover:text-slate-900',
              )}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="mt-4 flex-1 min-h-0 overflow-hidden">
        <div
          id={panelId('run')}
          role="tabpanel"
          aria-labelledby={tabId('run')}
          hidden={activeTab !== 'run'}
          className="h-full overflow-auto"
        >
          <RunAgentTab />
        </div>

        <div
          id={panelId('previous')}
          role="tabpanel"
          aria-labelledby={tabId('previous')}
          hidden={activeTab !== 'previous'}
          className="h-full overflow-auto"
        >
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">Previous Runs</h3>
            <p className="mt-1 text-sm text-slate-600">Review prior agent runs and outputs.</p>
          </div>
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

