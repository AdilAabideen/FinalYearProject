import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { AgentStatCard as StatCard } from '../../agents/components/shared/AgentStatCard';

type TestCaseRunStatus = 'idle' | 'running' | 'passed' | 'failed';

type DiffState = {
  status: 'idle' | 'ready' | 'error';
  diff?: Record<string, unknown> | null;
  passed?: boolean | null;
  score?: number | null;
  swarmStatus?: string | null;
  error?: string;
};

type MasTestCaseDiffPanelProps = {
  hasSelectedCase: boolean;
  diffState?: DiffState;
  runStatus: TestCaseRunStatus;
  expectedAcuity: string;
  actualFinalEsiLevel: string;
};

export function MasTestCaseDiffPanel({
  hasSelectedCase,
  diffState,
  runStatus,
  expectedAcuity,
  actualFinalEsiLevel,
}: MasTestCaseDiffPanelProps) {
  if (!hasSelectedCase) {
    return (
      <div className='w-full border-b border-slate-200'>
        <p className='text-xl font-semibold text-slate-900 mb-2  p-3 '>Mas Difference Panel</p>
        <div className="  bg-white p-3 px-4 text-md text-slate-800">
          Please Select a Test case
        </div>
      </div>
    );
  }

  if (diffState?.status === 'error') {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        {diffState.error}
      </div>
    );
  }

  if (diffState?.status === 'ready' && diffState.diff) {
    return (
      <div className="pb-2">
        <section className="rounded-none border border-slate-200 bg-white">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 p-3">
            <p className='text-xl font-semibold text-slate-900 '>Mas Run Difference</p>
            <span
              className={[
                'inline-flex rounded-full border px-3 py-1 text-xs font-semibold',
                diffState.passed
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : 'border-rose-200 bg-rose-50 text-rose-700',
              ].join(' ')}
            >
              {diffState.passed ? 'Passed' : 'Failed'}
            </span>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-2 p-3">
            <StatCard label="Expected Answer" value={`Acuity ${expectedAcuity}`} tone="accent" />
            <StatCard
              label="Actual Answer"
              value={`Final ESI Level ${actualFinalEsiLevel}`}
              tone={diffState.passed ? 'positive' : 'danger'}
            />
          </div>
        </section>

        <div className="rounded-none border border-t-0 border-slate-200 bg-white p-4">
          <p className='text-lg font-semibold text-slate-900 '>Difference Output</p>

          <div className="mt-3 max-h-[min(32rem,55vh)] overflow-auto ">
            <JsonInspector value={diffState.diff} />
          </div>
        </div>
      </div>
    );
  }

  if (runStatus === 'passed' || runStatus === 'failed') {
    return (
      <div>
        <p className='text-xl font-semibold text-slate-900 mb-2 border-b border-slate-200 p-3 '>Mas Run Difference</p>
        <div className="  bg-white p-3 px-4 text-md text-slate-800">
          Difference not available for this Case
        </div>
      </div>
    );
  }

  return (
    <div>
      <p className='text-xl font-semibold text-slate-900 mb-2 border-b border-slate-200 p-3 '>Mas Run Difference</p>
      <div className="  bg-white p-3 px-4 text-md text-slate-800">
        Difference is not yet available, please wait till the test case execution is finished
      </div>
    </div>
  );
}
