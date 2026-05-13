import type { ReactNode } from 'react';
import { cn } from '../lib/cn';

type StatChipProps = {
  value: ReactNode;
  label: string;
  className?: string;
};

// Renders the stat chip.
export function StatChip({ value, label, className }: StatChipProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-200/60',
        className,
      )}
    >
      <span className="font-semibold text-slate-900">{value}</span>
      <span className="text-slate-500">{label}</span>
    </div>
  );
}

