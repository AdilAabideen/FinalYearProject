import { useId, useState } from 'react';
import type { AgentTestCaseRead } from '../../types/agentTests';
import { SegmentedTabs } from '../ui/SegmentedTabs';

type HarnessTabKey = 'cases' | 'results';
type FakeCaseStatus = 'running' | 'passed' | 'failed';

const tabs: Array<{ key: HarnessTabKey; label: string }> = [
  { key: 'cases', label: 'Test Cases' },
  { key: 'results', label: 'Test Results' },
];

const input_label_map: Record<string, string> = {
  age_years: 'Age (years)',
  chiefcomplaint: 'Chief Complaint',
  dbp: 'DBP',
  heartrate: 'Heart Rate',
  intime: 'Intime',
  o2sat: 'O2 Sat',
  pain: 'Pain',
  resprate: 'Resp Rate',
  sbp: 'SBP',
  temperature: 'Temperature',
  subject_id: 'Subject ID',
}

type CaseTagsProps = {
  label: string;
  value: string | number;
  label_map: Record<string, string>;
};

function CaseTags({ label, value, label_map }: CaseTagsProps) {
  const new_label = label_map[label];
  if (!label) return null;

  return (
    <div className="text-[10px] bg-slate-100 text-slate-700 px-2 py-1 rounded-sm">
      {new_label ? new_label : label}: {value}
    </div>
  );
}

function fakeCaseStatus(index: number, busy: boolean, runId: string | null, error: string | null) {
  if (busy) return 'running' satisfies FakeCaseStatus;
  if (error) return 'failed' satisfies FakeCaseStatus;
  if (runId) return index % 6 === 5 ? ('failed' satisfies FakeCaseStatus) : 'passed';
  return index === 0 ? ('running' satisfies FakeCaseStatus) : 'passed';
}

function CaseStatusIcon({ status }: { status: FakeCaseStatus }) {
  if (status === 'running') {
    return (
      <span aria-label="Running" className="inline-flex h-4 w-4 items-center justify-center">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-PrimaryBlue" />
      </span>
    );
  }

  if (status === 'failed') {
    return (
      <span aria-label="Failed" className="text-xs font-semibold text-rose-600">
        ×
      </span>
    );
  }

  return (
    <span aria-label="Passed" className="text-xs font-semibold text-emerald-600">
      ✓
    </span>
  );
}

function NormaliseTitle(title: string) {
  return title
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase());
}

type AgentTestRunDrawerProps = {
  agentName: string;
  runId: string | null;
  selectedCases: AgentTestCaseRead[];
  busy: boolean;
  error: string | null;
};

export default function AgentTestRunDrawer({
  agentName,
  runId,
  selectedCases,
  busy,
  error,
}: AgentTestRunDrawerProps) {
  const baseId = useId();
  const [activeTab, setActiveTab] = useState<HarnessTabKey>('results');

  function tabId(key: HarnessTabKey) {
    return `${baseId}-tab-${key}`;
  }

  function panelId(key: HarnessTabKey) {
    return `${baseId}-panel-${key}`;
  }

  return (
    <div className="flex min-h-0 flex-col gap-4 h-full overflow-y-hidden">
      <SegmentedTabs
        idBase={baseId}
        tabs={tabs}
        value={activeTab}
        onChange={setActiveTab}
        ariaLabel="Test harness tabs"
        className="max-w-sm"
      />
      <span className="sr-only">{agentName}</span>

      <div
        id={panelId('cases')}
        role="tabpanel"
        aria-labelledby={tabId('cases')}
        hidden={activeTab !== 'cases'}
        className="h-full"
      >
        <div className="grid h-full grid-cols-5 grid-rows-7 rounded-2xl border border-slate-200 bg-white overflow-y-hidden">
          <div className="col-span-2 row-span-7 min-h-0 overflow-auto border-r border-slate-200 pb-16">
            {selectedCases.length ? (
              <div className="divide-y divide-slate-200">
                {selectedCases.map((testCase, index) => {
                  const status = fakeCaseStatus(index, busy, runId, error);
                  return (
                    <div key={testCase.id} className="flex items-center justify-between p-4">
                      <div className="cursor-pointer min-w-0 space-y-1 hover:scale-[1.02] transition-all duration-300">
                        <p className="truncate text-sm font-semibold text-slate-900 leading-tight">
                          {NormaliseTitle(testCase.name)}
                        </p>
                        <div className="flex items-center gap-1 flex-wrap">
                          {
                            Object.entries(testCase.inputJson).map(([label, value]) => (
                              <CaseTags
                                key={label}
                                label={label}
                                value={value as string | number}
                                label_map={input_label_map}
                              />
                            ))
                          }

                        </div>

                      </div>
                      <div className="shrink-0">
                        <CaseStatusIcon status={status} />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500">No cases selected.</p>
            )}
          </div>
          <div className="col-span-3 row-span-1 border-b border-slate-200 p-4">
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
              {true ? (
                  <div className="flex flex-col gap-1">
                    <span className=" text-slate-900 text-2xl">Start Test Run</span>
                    <span className="text-slate-900 text-[15px]">
                      <button className=" ml-5 cursor-pointer w-[100px] inline-flex items-center justify-center rounded-xl bg-PrimaryBlue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-PrimaryBlue/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-300">
                        Start
                      </button>
                    </span>
                  </div>
              ):
                (
                  [
                    { title: 'Number of Cases', answer: selectedCases.length },
                    { title: 'Currently Running', answer: "3/7" },
                    { title: 'Completed', answer: '4/7' },
                    { title: 'Time Elapsed', answer: '100s' },

                  ].map(({title, answer}) => (
              <div key={title} className="flex flex-col gap-0.5">
                <span className="font-semibold text-slate-500 text-[13px]">{title}</span>
                <span className="text-slate-900 text-[15px]">{answer}</span>
              </div>
                  ))
              )}
            </div>
          </div>
          <div className="col-span-3 row-span-5 border-slate-200">

          </div>
        </div>
      </div>

      <div
        id={panelId('results')}
        role="tabpanel"
        aria-labelledby={tabId('results')}
        hidden={activeTab !== 'results'}
      >
        {busy ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Starting test run…
          </div>
        ) : null}

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {runId ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            Started test run <span className="font-mono text-xs font-semibold text-slate-900">{runId}</span>
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
            Results will appear here.
          </div>
        )}
      </div>
    </div>
  );
}
