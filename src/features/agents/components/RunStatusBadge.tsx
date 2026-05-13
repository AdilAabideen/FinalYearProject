import { cn } from '../../../shared/lib/cn';
import { formatStatusLabel, runStatusBadgeClass } from '../utils/status';

type RunStatusBadgeProps = {
  status: string;
  className?: string;
};

// Renders the run status badge.
export function RunStatusBadge({ status, className }: RunStatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1',
        runStatusBadgeClass(status),
        className,
      )}
    >
      {formatStatusLabel(status)}
    </span>
  );
}
