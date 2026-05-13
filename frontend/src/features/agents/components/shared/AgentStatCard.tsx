import { cn } from '../../../../shared/lib/cn';

export type AgentStatCardTone = 'default' | 'accent' | 'positive' | 'danger' | 'warning';

type AgentStatCardProps = {
  label: string;
  value: string;
  tone?: AgentStatCardTone;
  small?: boolean;
  className?: string;
};

// Renders the agent stat card.
export function AgentStatCard({
  label,
  value,
  tone = 'default',
  small = false,
  className,
}: AgentStatCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-3',
        tone === 'positive' && 'border-emerald-200 bg-emerald-50/70',
        tone === 'danger' && 'border-rose-200 bg-rose-50/70',
        tone === 'warning' && 'border-amber-200 bg-amber-50/80',
        tone === 'accent' && 'border-sky-200 bg-sky-50/70',
        tone === 'default' && 'border-slate-200 bg-white',
        className,
      )}
    >
      <p
        className={cn(
          'font-semibold uppercase tracking-wide text-slate-500',
          small ? 'text-[9px]' : 'text-[11px]',
        )}
      >
        {label}
      </p>
      <p className={cn('mt-1 font-semibold text-slate-900', small ? 'text-[11px]' : 'text-base')}>
        {value}
      </p>
    </div>
  );
}
