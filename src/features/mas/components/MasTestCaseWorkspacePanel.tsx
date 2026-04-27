import type { ReactNode } from 'react';
import { MasTabs } from './MasTabs';

type CaseTabKey = 'test_case' | 'traces' | 'output' | 'metrics' | 'diff';

type MasTestCaseWorkspacePanelProps = {
  tabs: Array<{ key: CaseTabKey; label: string }>;
  activeTab: CaseTabKey;
  onChangeTab: (tab: CaseTabKey) => void;
  children: ReactNode;
};

export function MasTestCaseWorkspacePanel({
  tabs,
  activeTab,
  onChangeTab,
  children,
}: MasTestCaseWorkspacePanelProps) {
  return (
    <div className="col-span-2 flex h-full min-h-0 flex-col border-l border-slate-200 bg-white p-0">
      <MasTabs
        tabs={tabs}
        activeKey={activeTab}
        onChange={onChangeTab}
        scrollable={true}
        minTabWidthClassName="min-w-36"
        buttonClassName="flex h-full cursor-pointer items-center border-r border-b border-slate-200 px-4 py-2 text-left transition-colors"
      />
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
