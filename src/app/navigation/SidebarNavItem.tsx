import { forwardRef } from 'react';
import { cn } from '../../shared/lib/cn';

type SidebarNavItemProps = {
  iconSrc: string;
  label: string;
  active?: boolean;
  collapsed?: boolean;
  onClick: () => void;
};

export const SidebarNavItem = forwardRef<HTMLButtonElement, SidebarNavItemProps>(
  ({ iconSrc, label, active, collapsed = false, onClick }, ref) => {
    const buttonBase =
      'group relative z-0 flex w-full items-center gap-3 rounded-xl rounded-l-none px-3 py-2.5 text-left text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white';
    const buttonActive = 'bg-slate-50 text-slate-900 shadow-sm ring-1 ring-slate-200/60';
    const buttonInactive = 'text-slate-700 hover:bg-slate-50 hover:text-slate-900';

    const iconBase = 'h-5 w-5 shrink-0 object-contain transition-opacity';
    const iconActive = 'opacity-100';
    const iconInactive = 'opacity-70 group-hover:opacity-100';

    return (
      <button
        ref={ref}
        type="button"
        onClick={onClick}
        aria-current={active ? 'page' : undefined}
        title={collapsed ? label : undefined}
        className={cn(buttonBase, active ? buttonActive : buttonInactive)}
      >
        <img
          alt=""
          src={iconSrc}
          className={cn(iconBase, active ? iconActive : iconInactive)}
          draggable={false}
        />
        {!collapsed ? <span>{label}</span> : null}
      </button>
    );
  },
);

SidebarNavItem.displayName = 'SidebarNavItem';
