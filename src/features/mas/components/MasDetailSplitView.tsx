import { useState } from 'react';
import type { MasCatalogDetail } from '../../../types/mas';
import { MasDiagram } from './MasDiagram';

type MasDetailSplitViewProps = {
  workflow: MasCatalogDetail;
};

type MasTabKey = 'diagram' | 'test-cases';

const tabs: Array<{ key: MasTabKey; label: string }> = [
  { key: 'diagram', label: 'MAS Diagram' },
  { key: 'test-cases', label: 'Test Cases' },
];

export function MasDetailSplitView({ workflow }: MasDetailSplitViewProps) {
  const [activeTab, setActiveTab] = useState<MasTabKey>('diagram');

  return (
    <div className="grid h-full min-h-0 p-0 lg:grid-cols-1">
      <section className="flex min-h-0 flex-col border-r border-slate-200 p-0">
        <div className="flex h-11 items-stretch border-b border-slate-200 bg-white">
          {tabs.map((tab) => {
            const active = activeTab === tab.key;

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={[
                  'flex h-full min-w-36 items-center border-r border-slate-200 px-4 text-left transition-colors',
                  active ? 'bg-slate-50' : 'bg-white hover:bg-slate-50',
                ].join(' ')}
              >
                <p
                  className={[
                    'text-sm font-semibold',
                    active ? 'text-slate-900' : 'text-slate-500',
                  ].join(' ')}
                >
                  {tab.label}
                </p>
              </button>
            );
          })}
        </div>

        {activeTab === 'diagram' ? (
          <div className="min-h-[560px] flex-1 overflow-hidden rounded-none bg-white">
            <MasDiagram workflow={workflow} />
          </div>
        ) : (
          <div className="flex min-h-[560px] flex-1 items-center justify-center bg-white p-6">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-6 py-8 text-center shadow-sm">
              <p className="text-sm font-semibold text-slate-900">Test Cases</p>
              <p className="mt-2 text-sm text-slate-500">
                Test case rendering for MAS workflows can be added here next.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
