import { useRef, useState } from 'react';
import type { MasCatalogDetail } from '../../../types/mas';
import { DEFAULT_MAS_WORKFLOW_INPUT } from '../config/defaultWorkflowInput';
import { AgentInputForm } from '../../agents/components/AgentInputForm';
import { MasDiagram } from './MasDiagram';
import MasResultsTab from './MasResultsTab';
import MasTracesTab from './MasTracesTab';
import { masRunService } from '../../../services/masRunService';
import { coerceInputForRun } from '../utils/jsonSchema';
import type { SwarmExecutionStartResponse } from '../../../types/masRuns';

type MasDetailSplitViewProps = {
  workflow: MasCatalogDetail;
};

type MasTabKey = 'diagram' | 'test-cases';
type ResultTabKey = 'traces' | 'output'

const tabs: Array<{ key: MasTabKey; label: string }> = [
  { key: 'diagram', label: 'MAS Diagram' },
  { key: 'test-cases', label: 'Test Cases' },
];

const resultTabs: Array<{ key: ResultTabKey; label: string }> = [
  { key: 'traces', label: 'Traces' },
  { key: 'output', label: 'Output' },
]

export function MasDetailSplitView({ workflow }: MasDetailSplitViewProps) {
  const [activeTab, setActiveTab] = useState<MasTabKey>('diagram');
  const [workflowInputValue, setWorkflowInputValue] = useState<Record<string, unknown>>(() => ({
    ...DEFAULT_MAS_WORKFLOW_INPUT,
  }));
  const [submitted, setSubmitted] = useState(false);
  const [activeResultTab, setActiveResultTab] = useState<ResultTabKey>('traces');
  const [runInfo, setRunInfo] = useState<SwarmExecutionStartResponse>({} as SwarmExecutionStartResponse);
  const abortRef = useRef<AbortController | null>(null);


  async function handleSubmitInput() {

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    const payload = coerceInputForRun(workflow.input_schema.json_schema, workflowInputValue)
    console.log(JSON.stringify({
      input: payload
    }))

    try {
      const mas_run_details : SwarmExecutionStartResponse = await masRunService.startMasRun(
        workflow.metadata.workflow_id,
        payload,
        ac.signal
      )
      console.log("Success", mas_run_details)
      setRunInfo(mas_run_details)
      if (ac.signal.aborted) return;
    } catch (e: unknown) {
      if (ac.signal.aborted) return;
      console.error("Error : ", e)
    } finally {
      setSubmitted(true)
    }

  }

  return (
    <div className="grid h-full min-h-0 p-0 lg:grid-cols-1">
      <section className="flex min-h-0 flex-col border-r border-slate-200 p-0">
        <div className="flex  items-stretch border-b border-slate-200 bg-white">
          {tabs.map((tab) => {
            const active = activeTab === tab.key;

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={[
                  'flex h-full min-w-36 py-2 items-center border-r border-slate-200 px-4 text-left transition-colors',
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
          <div className="grid h-full grid-cols-6 grid-rows-1">
            <div className="min-h-[560px] col-span-4 flex-1 overflow-hidden rounded-none bg-white">
              <MasDiagram workflow={workflow} />
            </div>
            <div className="col-span-2 border-l border-slate-200 bg-white">
              <div className="flex h-full min-h-[560px] flex-col overflow-hidden">
                <div className="min-h-0 flex-1 overflow-hidden">
                  <div className="flex h-full min-h-0 flex-col rounded-none border border-slate-200 bg-white">


                    {
                      !submitted ? (
                        <>
                          <div className="shrink-0 border-b border-slate-300 p-2 px-4 pt-3">
                            <p className="text-md font-semibold text-slate-900">Workflow Input</p>
                          </div>
                          <AgentInputForm
                            schema={workflow.input_schema.json_schema}
                            value={workflowInputValue}
                            onChange={setWorkflowInputValue}
                            submitButtonLabel="Submit Input"
                            onSubmit={handleSubmitInput}
                            className="flex-1 min-h-0 mb-10"
                          />
                        </>
                      ) : (
                        <>
                          <div className=" border-b border-slate-300 flex flex-row">
                            {resultTabs.map((tab) => {
                              const active = activeResultTab === tab.key;

                              return (
                                <button
                                  key={tab.key}
                                  type="button"
                                  onClick={() => setActiveResultTab(tab.key)}
                                  className={[
                                    'flex h-full min-w-3 py-2 items-center border-r border-slate-200 px-4 text-left transition-colors',
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
                          {
                            activeResultTab == 'traces' ? (
                              <MasTracesTab agentNames={workflow.participating_agents} eventsStreamUrl={runInfo? runInfo.eventsStreamUrl : ""} swarm_run_id={runInfo.swarmRunId} />
                            ) :
                              (
                                <MasResultsTab input={workflowInputValue} />

                              )
                          }

                        </>
                      )
                    }
                  </div>
                </div>
              </div>
            </div>
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
