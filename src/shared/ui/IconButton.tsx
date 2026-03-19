import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '../lib/cn';

type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> & {
  children: ReactNode;
};

export function IconButton({ className, children, type, ...props }: IconButtonProps) {
  return (
    <button
      type={type ?? 'button'}
      className={cn(
        'inline-flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white shadow-sm transition hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:bg-slate-900',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
