import type { MasTestRunResults } from '../../../types/masTests';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { AgentStatCard as StatCard } from '../../agents/components/shared/AgentStatCard';
import { formatDuration, formatInteger, formatLatencyMs, formatPercent } from '../../agents/utils/format';

type MasBatchOutputPanelProps = {
  status: 'idle' | 'loading' | 'error' | 'ready';
  error?: string;
  results: MasTestRunResults | null;
};

type TableTitleProps = {
  title: string;
};

const TableTitle: React.FC<TableTitleProps> = ({ title }) => {
  return <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</th>;
};

// Renders the MAS batch output panel.
export function MasBatchOutputPanel({ status, error, results }: MasBatchOutputPanelProps) {
  if (status === 'idle') {
    return (
      <div className=" bg-white p-4 text-md text-slate-700 ">
        <p className='text-xl font-semibold text-slate-900 mb-2  border-slate-200 '>MAS Test Outputs</p>

        Please Start and finish a MAS test run to view batch output.
      </div>
    );
  }

  if (status === 'loading') {
    return (
      <div className=" bg-white p-4 text-md text-slate-700 ">
        <p className='text-xl font-semibold text-slate-900 mb-2  border-slate-200 '>MAS Test Outputs</p>

        Loading MAS Test run results
      </div>
    );
  }

  if (status === 'error') {
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>;
  }

  if (!results) return null;

  return (
    <div className="space-y-4 pb-3">
      <section className="border border-slate-200 border-b-0 bg-white">
        <div className="flex flex-wrap items-start justify-between gap-3 p-4 pb-0">
          <div>
            <p className="text-xl font-semibold text-slate-900">{results.run.name || 'MAS Test Run Output'}</p>
            <p className="mt-1 text-sm text-slate-700">Workflow: {results.run.workflowId}</p>
            <p className="mt-1 text-xs text-slate-500">
              Started: {results.run.startedAt ?? '—'} · Finished: {results.run.finishedAt ?? '—'}
            </p>
          </div>
          <div
            className={[
              'rounded-full border px-3 py-1 text-xs font-semibold',
              results.run.status.toLowerCase().includes('fail')
                ? 'border-rose-200 bg-rose-50 text-rose-700'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700',
            ].join(' ')}
          >
            {results.run.status.slice(0,1).toUpperCase() + results.run.status.slice(1)}
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 p-4 pt-0">
          <StatCard label="Total Cases" value={formatInteger(results.summary.totalRuns)} tone="accent" />
          <StatCard label="Passed" value={formatInteger(results.summary.successfulRuns)} tone="positive" />
          <StatCard
            label="Failed"
            value={formatInteger(results.summary.failedRuns)}
            tone={results.summary.failedRuns > 0 ? 'danger' : 'default'}
          />
          <StatCard label="Accuracy" value={formatPercent(results.summary.successRate)} tone="accent" />
          <StatCard
            label="Execution Failed"
            value={formatInteger(results.summary.executionFailedCount)}
            tone={results.summary.executionFailedCount > 0 ? 'danger' : 'default'}
          />
          <StatCard
            label="Missing Final Output"
            value={formatInteger(results.summary.missingFinalOutputCount)}
            tone={results.summary.missingFinalOutputCount > 0 ? 'danger' : 'default'}
          />
          <StatCard
            label="Avg Duration"
            value={formatDuration(
              results.summary.durationMsAvg == null ? null : results.summary.durationMsAvg / 1000,
            )}
          />
          <StatCard label="Runs With MAS" value={formatInteger(results.summary.runsWithSwarmRun)} />
        </div>
      </section>

      <section className="border-t border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-lg font-semibold text-slate-900">Case Results</p>
          <p className="text-xs text-slate-500">{results.cases.length} rows</p>
        </div>
        <div className="mt-3 overflow-auto rounded-2xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <TableTitle title="Case Name" />
                <TableTitle title="Case ID" />
                <TableTitle title="MAS Run ID" />
                <TableTitle title="Status" />
                <TableTitle title="Passed" />
                <TableTitle title="Score" />
                <TableTitle title="Failure Reason" />
                <TableTitle title="MAS Status" />
                <TableTitle title="Duration" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {results.cases.map((item) => (
                <tr key={item.testCaseId} className="hover:bg-slate-50/70">
                  <td className="px-4 py-3 text-sm font-medium text-slate-900">{item.testCaseName}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{item.testCaseId}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{item.swarmRunId ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{item.status}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">
                    {item.passed == null ? '—' : item.passed ? 'Yes' : 'No'}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">{item.score == null ? '—' : String(item.score)}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{item.failureReason ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{item.swarmStatus ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{formatLatencyMs(item.durationMs)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <details className="border-l-0 border-r-0 border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
          Raw Results JSON
        </summary>
        <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <JsonInspector value={results} />
        </div>
      </details>
    </div>
  );
}
