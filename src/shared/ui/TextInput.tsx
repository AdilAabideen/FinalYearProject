import { useId, type InputHTMLAttributes } from 'react';
import { cn } from '../lib/cn';

type TextInputProps = InputHTMLAttributes<HTMLInputElement> & {
  srLabel: string;
};

export function TextInput({ srLabel, className, id, ...props }: TextInputProps) {
  const autoId = useId();
  const resolvedId = id ?? autoId;

  return (
    <div>
      <label className="sr-only" htmlFor={resolvedId}>
        {srLabel}
      </label>
      <input
        id={resolvedId}
        className={cn(
          'rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700 placeholder:text-slate-400 shadow-sm disabled:cursor-not-allowed disabled:opacity-70',
          className,
        )}
        {...props}
      />
    </div>
  );
}

