import { useEffect, useRef, useState } from 'react';
import type { MasTestCaseRead } from '../../../types/masTests';
import { masTestService } from '../../../services/masTestService';
import type { MasCatalogDetail } from '../../../types/mas';
import { MasDiagram } from './MasDiagram';
import { JsonInspector } from '../../../shared/ui/JsonInspector';

type MasTestCasesProps = {
  workflow: MasCatalogDetail;
};

type TestCaseTabKey = 'test_case' | 'traces' | 'output' | 'metrics';

type TestCaseTab = {
  key: TestCaseTabKey;
  label: string;
};

const testCaseTabs: TestCaseTab[] = [
  { key: 'test_case', label: 'Test Case' },
  { key: 'traces', label: 'Traces' },
  { key: 'output', label: 'Output' },
  { key: 'metrics', label: 'Metrics' },
];

function splitName(name: string) {
  return name.split('-', 1)[0];
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export default function MasTestCases({ workflow }: MasTestCasesProps) {
  const [testCases, setTestCases] = useState<MasTestCaseRead[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const [selectedTestCase, setSelectedTestCase] = useState<MasTestCaseRead | null>(null);
  const [activeTab, setActiveTab] = useState<TestCaseTabKey>('test_case');

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    async function loadTestCases(workflow_id: string) {
      setLoading(true);

      try {
        if (workflow_id) {
          const loadedTestCases = await masTestService.listTestCases(
            { workflow_id },
            ac.signal,
          );
          if (ac.signal.aborted) return;
          setTestCases(loadedTestCases);
          setSelectedTestCase((prev) => prev ?? loadedTestCases[0] ?? null);
        }
      } catch (e) {
        if (ac.signal.aborted) return;
        console.error('Error occurred', e);
        setTestCases([]);
      } finally {
        if (!ac.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadTestCases(workflow?.metadata.workflow_id);

    return () => {
      ac.abort();
    };
  }, [workflow?.metadata.workflow_id]);

  if (loading) {
    return (
      <div className="flex min-h-[560px] h-full flex-1 items-center justify-center bg-white p-6">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-6 py-8 text-center shadow-sm">
          <p className="text-sm font-semibold text-slate-900">Loading test cases…</p>
        </div>
      </div>
    );
  }

  return testCases?.length > 0 ? (
    <div className="h-full min-h-0 overflow-auto bg-white flex flex-col w-full">
      <div className="flex flex-row p-0 items-start ">
        {testCases?.map((test) => {
          const active = selectedTestCase?.id === test.id;
          return (
            <button
              key={test.id}
              type="button"
              onClick={() => setSelectedTestCase(test)}
              className={[
                'flex h-full cursor-pointer min-w-36 py-2 items-center border-r border-b border-slate-200 px-4 text-left transition-colors',
                active ? 'bg-slate-50' : 'bg-white hover:bg-slate-50',
              ].join(' ')}
            >
              <p
                className={[
                  'text-sm font-semibold',
                  active ? 'text-slate-900' : 'text-slate-500',
                ].join(' ')}
              >
                {'Test ' + splitName(test.name)}
              </p>
            </button>
          );
        })}
      </div>
      <div className="grid h-full min-h-[560px] grid-cols-6 grid-rows-1">
        <div className="relative col-span-4 h-full min-h-0 flex-1 overflow-hidden rounded-none bg-white">
          <MasDiagram
            workflow={workflow}
          />
          <div className="absolute bottom-3 left-3 z-10 ">
            <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white/95 px-3 py-2 shadow-sm backdrop-blur">
              <div className="min-w-0">
                <p className="text-[15px] font-semibold uppercase tracking-wide text-slate-500">
                  Start Test Cases
                </p>
                <p className="text-md font-medium text-slate-900">
                  {testCases.length} {testCases.length === 1 ? 'test' : 'tests'}
                </p>
              </div>
              <button
                type="button"
                className="inline-flex  items-center justify-center rounded-lg border border-PrimaryBlue/20 bg-PrimaryBlue px-3 py-1.5 cursor-pointer text-md font-semibold text-white transition hover:bg-PrimaryBlue/90"
              >
                Start Tests
              </button>
            </div>
          </div>
        </div>
        <div className="col-span-2 min-h-0 border-l border-slate-200 bg-white">
          <div className="flex flex-row p-0 items-start">
            {testCaseTabs.map((tab) => {
              const active = activeTab === tab.key;

              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={[
                    'flex h-full cursor-pointer min-w-36 py-2 items-center border-r border-b border-slate-200 px-4 text-left transition-colors',
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
          <div className="p-4">
            {activeTab === 'test_case' ? (
              selectedTestCase ? (
                <div className="space-y-4">
                  <section className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Test Case
                        </p>
                        <p className="mt-1 text-base font-semibold text-slate-900">
                          {selectedTestCase.name}
                        </p>
                      </div>
                      <div
                        className={[
                          'rounded-full border px-3 py-1 text-xs font-semibold',
                          selectedTestCase.enabled
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : 'border-slate-200 bg-slate-50 text-slate-600',
                        ].join(' ')}
                      >
                        {selectedTestCase.enabled ? 'Enabled' : 'Disabled'}
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                          Created At
                        </p>
                        <p className="mt-1 text-sm text-slate-700">
                          {formatDateTime(selectedTestCase.createdAt)}
                        </p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                          Updated At
                        </p>
                        <p className="mt-1 text-sm text-slate-700">
                          {formatDateTime(selectedTestCase.updatedAt)}
                        </p>
                      </div>
                    </div>
                  </section>

                  <details className="rounded-2xl border border-slate-200 bg-white p-4" open>
                    <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
                      Input JSON
                    </summary>
                    <div className="mt-3 max-h-[min(22rem,40vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <JsonInspector value={selectedTestCase.inputJson} />
                    </div>
                  </details>

                  <details className="rounded-2xl border border-slate-200 bg-white p-4" open>
                    <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
                      Expected JSON
                    </summary>
                    <div className="mt-3 max-h-[min(22rem,40vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <JsonInspector value={selectedTestCase.expectedJson} />
                    </div>
                  </details>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
                  <p className="text-sm font-semibold text-slate-900">No test case selected.</p>
                </div>
              )
            ) : activeTab === 'traces' ? (
              <p className="text-sm text-slate-700">Traces</p>
            ) : activeTab === 'output' ? (
              <p className="text-sm text-slate-700">Output</p>
            ) : (
              <p className="text-sm text-slate-700">Metrics</p>
            )}
          </div>
        </div>
      </div>
    </div>
  ) : (
    <div className="flex min-h-[560px] h-full flex-1 items-center justify-center bg-white p-6">
      <div className="flex  items-stretch border-b border-slate-200 bg-white">
        No tests
      </div>
    </div>
  );
}
