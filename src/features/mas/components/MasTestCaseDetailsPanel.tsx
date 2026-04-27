import type { MasTestCaseRead } from '../../../types/masTests';
import { JsonInspector } from '../../../shared/ui/JsonInspector';

type MasTestCaseDetailsPanelProps = {
  testCase: MasTestCaseRead | null;
};

export function MasTestCaseDetailsPanel({ testCase }: MasTestCaseDetailsPanelProps) {
  if (!testCase) {
    return (
      <div className="p-4">
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
          <p className="text-sm font-semibold text-slate-900">No test case selected.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 overflow-auto ">
      <div className="space-y-0">
        <section className=" bg-white">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 p-4 pb-1 px-3">Test Case</p>
              <p className='text-xl font-semibold text-slate-900 mb-2  p-3 pt-0 pb-1 '>{testCase.name}</p>

            </div>
            <div
              className={[
                'rounded-full border px-3 py-1 text-xs font-semibold m-2',
                testCase.enabled
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : 'border-slate-200 bg-slate-50 text-slate-600',
              ].join(' ')}
            >
              {testCase.enabled ? 'Enabled' : 'Disabled'}
            </div>
          </div>


        </section>

        <div className=" border-t border-slate-200 bg-white p-3 mt-0  border-b" >
          <p className='text-md font-semibold text-slate-900 mb-2  border-slate-200 '>Input JSON</p>
          <div className="mt-3 max-h-[min(25rem,40vh)] overflow-auto pt-0  p-3">
            <JsonInspector value={testCase.inputJson} />
          </div>
        </div>

        <div className=" bg-white p-4 pt-4">
          <p className='text-md font-semibold text-slate-900 mb-2  border-slate-200 '>Expected JSON</p>
          <div className="mt-3 max-h-[min(22rem,40vh)] overflow-auto pt-0 p-3">
            <JsonInspector value={testCase.expectedJson} />
          </div>
        </div>
      </div>
    </div>
  );
}
