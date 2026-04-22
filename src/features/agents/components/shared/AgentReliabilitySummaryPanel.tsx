import { titleCaseKey, formatInteger } from '../../utils/format';
import type { ReliabilitySummaryView } from '../../utils/reliability';
import { AgentStatCard } from './AgentStatCard';

type AgentReliabilitySummaryPanelProps = {
  summaryView: ReliabilitySummaryView;
  statusSmall?: boolean;
};

export function AgentReliabilitySummaryPanel({
  summaryView,
  statusSmall = false,
}: AgentReliabilitySummaryPanelProps) {
  return (
    <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Reliability Summary</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <AgentStatCard label="Total Issues" value={formatInteger(summaryView.totalIssues)} tone="accent" />
        <AgentStatCard
          label="Error Issues"
          value={formatInteger(summaryView.errorIssues)}
          tone={summaryView.available ? (summaryView.hasErrors ? 'danger' : 'default') : 'default'}
        />
        <AgentStatCard
          label="Warning Issues"
          value={formatInteger(summaryView.warningIssues)}
          tone={summaryView.available ? (summaryView.hasWarnings ? 'warning' : 'positive') : 'default'}
        />
        <AgentStatCard
          label="Info Issues"
          value={formatInteger(summaryView.infoIssues)}
          tone={summaryView.available ? 'accent' : 'default'}
        />
        <AgentStatCard
          label="Reliability Status"
          value={summaryView.statusLabel}
          tone={summaryView.statusTone}
          small={statusSmall}
        />
      </div>

      {summaryView.byCategory.length ? (
        <div className="mt-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">By Category</p>
          <div className={`mt-2 grid w-full gap-3 ${summaryView.gridColumnsClass}`}>
            {summaryView.byCategory.map((item) => {
              const toneClass =
                item.severity === 'error'
                  ? 'border-rose-200 bg-rose-50/70 text-rose-900'
                  : item.severity === 'warning'
                    ? 'border-amber-200 bg-amber-50/80 text-amber-900'
                    : 'border-sky-200 bg-sky-50/70 text-sky-900';
              return (
                <div key={`${item.issueCode}-${item.severity}`} className={`min-h-44 rounded-xl border p-3 ${toneClass}`}>
                  <div className="flex h-full flex-col justify-between">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wide opacity-80">Issue Code</p>
                      <p className="mt-1 text-sm font-semibold">{titleCaseKey(item.issueCode)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wide opacity-80">Severity</p>
                      <p className="mt-1 text-xs font-semibold uppercase tracking-wide">{item.severity}</p>
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wide opacity-80">Count</p>
                      <p className="mt-1 text-lg font-semibold">{formatInteger(item.count)}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
