import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '../../shared/lib/cn';

type SidebarFooterButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> & {
  children: ReactNode;
};

export function SidebarFooterButton({
  className,
  children,
  type,
  ...props
}: SidebarFooterButtonProps) {
  return (
    <button
      type={type ?? 'button'}
      className={cn(
        'w-full rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

