import { cn } from '../../../shared/lib/cn';
import { toolStatusBadgeClass, type ToolStatus } from '../utils/status';

type ToolStatusBadgeProps = {
  status: ToolStatus;
  className?: string;
};

// Renders the tool status badge.
export function ToolStatusBadge({ status, className }: ToolStatusBadgeProps) {
  const label = status === 'succeeded' ? 'succeeded' : status === 'error' ? 'error' : 'unknown';
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1',
        toolStatusBadgeClass(status),
        className,
      )}
    >
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}
