import arrowRightIcon from '../../../assets/figma/icon-arrow-right.png';
import { Badge } from '../../../shared/ui/Badge';
import { IconButton } from '../../../shared/ui/IconButton';
import { StatChip } from '../../../shared/ui/StatChip';

type MasCardProps = {
  workflowId: string;
  name: string;
  version: string;
  description?: string;
  participatingAgentsCount: number;
  startAgentsCount: number;
  finalizingAgentsCount: number;
  gatesCount: number;
  sourcesCount: number;
  onOpen?: (workflowId: string) => void;
};

export function MasCard({
  workflowId,
  name,
  version,
  description,
  participatingAgentsCount,
  startAgentsCount,
  finalizingAgentsCount,
  gatesCount,
  sourcesCount,
  onOpen,
}: MasCardProps) {
  const openDisabled = !onOpen;

  return (
    <div
      role={openDisabled ? undefined : 'button'}
      tabIndex={openDisabled ? -1 : 0}
      className="group flex w-full min-h-[230px] flex-col rounded-2xl border border-slate-200 border-t-4 border-t-PrimaryBlue bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
      onClick={openDisabled ? undefined : () => onOpen?.(workflowId)}
      onKeyDown={
        openDisabled
          ? undefined
          : (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onOpen?.(workflowId);
              }
            }
      }
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="truncate text-xl font-semibold text-slate-900">{name}</h2>
        </div>
        <Badge>v{version}</Badge>
      </div>

      {description ? <p className="mt-2 text-sm text-slate-600">{description}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <StatChip value={participatingAgentsCount} label="Agents" />
        <StatChip value={startAgentsCount} label="Starts" />
        <StatChip value={finalizingAgentsCount} label="Finalizers" />
        <StatChip value={gatesCount} label="Gates" />
        <StatChip value={sourcesCount} label="Sources" />
      </div>

      <IconButton
        className="ml-auto mt-6"
        aria-label={openDisabled ? `${name} (coming soon)` : `Open ${name}`}
        disabled={openDisabled}
        title={openDisabled ? 'Coming soon' : undefined}
        onClick={(e) => {
          e.stopPropagation();
          onOpen?.(workflowId);
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

export function MasCardSkeleton() {
  return (
    <div className="flex w-full min-h-[230px] flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="h-6 w-40 animate-pulse rounded bg-slate-200" />
          <div className="mt-2 h-3 w-24 animate-pulse rounded bg-slate-200" />
        </div>
        <div className="h-6 w-16 animate-pulse rounded-full bg-slate-200" />
      </div>
      <div className="mt-3 space-y-2">
        <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <div className="h-8 w-24 animate-pulse rounded-lg bg-slate-200" />
        <div className="h-8 w-24 animate-pulse rounded-lg bg-slate-200" />
        <div className="h-8 w-24 animate-pulse rounded-lg bg-slate-200" />
      </div>
      <div className="mt-6 ml-auto h-10 w-10 animate-pulse rounded-xl bg-slate-200" />
    </div>
  );
}
