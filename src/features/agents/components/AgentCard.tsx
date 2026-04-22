import arrowRightIcon from '../../../assets/figma/icon-arrow-right.png';
import { Badge } from '../../../shared/ui/Badge';
import { IconButton } from '../../../shared/ui/IconButton';
import { StatChip } from '../../../shared/ui/StatChip';

type AgentCardProps = {
  name: string;
  title: string;
  description?: string;
  toolsCount: number;
  onOpen?: (agentName: string) => void;
};

export function AgentCard({ name, title, description, toolsCount, onOpen }: AgentCardProps) {
  const openDisabled = !onOpen;

  return (
    <div
      role={openDisabled ? undefined : 'button'}
      tabIndex={openDisabled ? -1 : 0}
      className="group flex w-full h-[230px] flex-col rounded-2xl border border-slate-200 border-t-4 border-t-PrimaryBlue bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
      onClick={openDisabled ? undefined : () => onOpen?.(name)}
      onKeyDown={
        openDisabled
          ? undefined
          : (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onOpen?.(name);
              }
            }
      }
    >
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
        <Badge>Ready</Badge>
      </div>

      {description ? <p className="mt-2 text-sm text-slate-600">{description}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <StatChip value={toolsCount} label="Tools" />
      </div>

      <IconButton
        className="ml-auto mt-6"
        aria-label={openDisabled ? `${title} (coming soon)` : `Open ${title}`}
        disabled={openDisabled}
        title={openDisabled ? 'Coming soon' : undefined}
        onClick={(e) => {
          e.stopPropagation();
          onOpen?.(name);
        }}
      >
        <img
          alt=""
          src={arrowRightIcon}
          className="h-5 w-5 object-contain invert transition-transform group-hover:translate-x-0.5"
          draggable={false}
        />
      </IconButton>
    </div>
  );
}

export function AgentCardSkeleton() {
  return (
    <div className="flex w-full max-w-sm flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="h-6 w-40 animate-pulse rounded bg-slate-200" />
        <div className="h-6 w-14 animate-pulse rounded-full bg-slate-200" />
      </div>
      <div className="mt-3 space-y-2">
        <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
      </div>
      <div className="mt-4">
        <div className="h-8 w-28 animate-pulse rounded-lg bg-slate-200" />
      </div>
      <div className="mt-6 ml-auto h-10 w-10 animate-pulse rounded-xl bg-slate-200" />
    </div>
  );
}
