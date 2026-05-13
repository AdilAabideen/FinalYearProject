import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '../../shared/lib/cn';

type SidebarFooterButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> & {
  children: ReactNode;
  collapsed?: boolean;
};

// Renders the sidebar footer button.
export function SidebarFooterButton({
  className,
  children,
  collapsed = false,
  type,
  ...props
}: SidebarFooterButtonProps) {
  return (
    <button
      type={type ?? 'button'}
      title={collapsed ? String(children) : undefined}
      className={cn(
        'w-full rounded-xl px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white',
        collapsed ? 'text-center' : 'text-left',
        className,
      )}
      {...props}
    >
      {collapsed ? 'Docs' : children}
    </button>
  );
}
