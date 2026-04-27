import type { MasTestCaseRead } from '../../../types/masTests';
import { MasTabs } from './MasTabs';
import { splitMasTestCaseName } from '../utils/format';

type TestCaseRunStatus = 'idle' | 'running' | 'passed' | 'failed';

type MasSelectedCaseTabsProps = {
  visibleTestCases: MasTestCaseRead[];
  selectedTestCaseId: string | null;
  runStatuses: Record<string, TestCaseRunStatus>;
  onSelectCase: (testCase: MasTestCaseRead) => void;
};

export function MasSelectedCaseTabs({
  visibleTestCases,
  selectedTestCaseId,
  runStatuses,
  onSelectCase,
}: MasSelectedCaseTabsProps) {
  return (
    <MasTabs
      tabs={visibleTestCases.map((testCase) => ({
        key: testCase.id,
        label: `Test ${splitMasTestCaseName(testCase.name)}`,
      }))}
      activeKey={selectedTestCaseId ?? ''}
      onChange={(testCaseId) => {
        const next = visibleTestCases.find((testCase) => testCase.id === testCaseId);
        if (next) onSelectCase(next);
      }}
      scrollable={true}
      wrapperClassName="border-b border-slate-200"
      minTabWidthClassName="min-w-36"
      buttonClassName="flex h-full cursor-pointer items-center border-r border-t border-slate-200 px-4 py-2 text-left transition-colors"
      renderPrefix={(tab) => {
        const runStatus = runStatuses[tab.key] ?? 'idle';

        return (
          <span
            className={[
              'mr-2 inline-block h-2.5 w-2.5 rounded-full',
              runStatus === 'passed'
                ? 'bg-emerald-500'
                : runStatus === 'failed'
                  ? 'bg-rose-500'
                  : runStatus === 'running'
                    ? 'bg-amber-500'
                    : 'bg-slate-300',
            ].join(' ')}
          />
        );
      }}
    />
  );
}
