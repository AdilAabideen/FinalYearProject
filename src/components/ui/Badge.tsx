import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';

type BadgeProps = {
  children: ReactNode;
  className?: string;
};

export function Badge({ children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full bg-PrimaryBlue/10 px-2.5 py-1 text-xs font-semibold text-PrimaryBlue ring-1 ring-PrimaryBlue/20',
        className,
      )}
    >
      {children}
    </span>
  );
}

