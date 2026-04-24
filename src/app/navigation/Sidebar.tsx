import { useLayoutEffect, useRef, useState } from 'react';
import agentsIcon from '../../assets/figma/icon-agents.png';
import homeIcon from '../../assets/figma/icon-home.png';
import { SidebarBrand } from './SidebarBrand';
import { SidebarFooterButton } from './SidebarFooterButton';
import { SidebarNavItem } from './SidebarNavItem';

export type NavKey = 'home' | 'agents' | 'mas';

type SidebarProps = {
  active: NavKey;
  onNavigate: (key: NavKey) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export function Sidebar({ active, onNavigate, collapsed, onToggleCollapsed }: SidebarProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const homeRef = useRef<HTMLButtonElement | null>(null);
  const agentsRef = useRef<HTMLButtonElement | null>(null);
  const masRef = useRef<HTMLButtonElement | null>(null);

  const [{ y, height, visible }, setIndicator] = useState({ y: 0, height: 0, visible: false });

  useLayoutEffect(() => {
    let frame: number | null = null;

    const update = () => {
      const container = listRef.current;
      let target;

      if (active === 'home') {
        target = homeRef.current;
      } else if (active === 'mas') {
        target = masRef.current;
      } else {
        target = agentsRef.current;
      }

      if (!container || !target) {
        setIndicator((prev) => (prev.visible ? { ...prev, visible: false } : prev));
        return;
      }

      const containerRect = container.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const nextY = Math.round(targetRect.top - containerRect.top);
      const nextHeight = Math.round(targetRect.height);
      setIndicator({ y: nextY, height: nextHeight, visible: true });
    };

    const schedule = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(update);
    };

    schedule();

    const onResize = () => schedule();
    window.addEventListener('resize', onResize);

    const ro = new ResizeObserver(() => schedule());
    if (listRef.current) ro.observe(listRef.current);
    if (homeRef.current) ro.observe(homeRef.current);
    if (agentsRef.current) ro.observe(agentsRef.current);
    if (masRef.current) ro.observe(masRef.current);

    let cancelled = false;
    document.fonts?.ready?.then(() => {
      if (!cancelled) schedule();
    });

    return () => {
      cancelled = true;
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener('resize', onResize);
      ro.disconnect();
    };
  }, [active]);

  return (
    <aside
      className={[
        'flex shrink-0 flex-col border-r border-slate-200 bg-white transition-[width] duration-200 ease-out',
        collapsed ? 'w-20' : 'w-64',
      ].join(' ')}
    >
      <div
        className={[
          'px-3 py-3',
          collapsed ? 'flex flex-col items-center gap-2' : 'flex items-start justify-between gap-2',
        ].join(' ')}
      >
        <SidebarBrand collapsed={collapsed} />
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        >
          <span className={collapsed ? 'translate-x-0.5' : ''}>{collapsed ? '»' : '«'}</span>
        </button>
      </div>

      <nav className={collapsed ? 'px-2' : 'px-4'} aria-label="Primary">
        <div ref={listRef} className="relative space-y-2">
          <span
            aria-hidden="true"
            className={[
              'pointer-events-none absolute left-0 top-0 w-1 z-10 rounded-r-full bg-PrimaryBlue shadow-sm transition-[transform,height,opacity] duration-200 ease-out motion-reduce:transition-none',
              visible ? 'opacity-100' : 'opacity-0',
            ].join(' ')}
            style={{ transform: `translateY(${y}px)`, height: `${height}px` }}
          />
          <SidebarNavItem
            ref={homeRef}
            onClick={() => onNavigate('home')}
            iconSrc={homeIcon}
            label="Home"
            active={active === 'home'}
            collapsed={collapsed}
          />

          <SidebarNavItem
            ref={agentsRef}
            onClick={() => onNavigate('agents')}
            iconSrc={agentsIcon}
            label="Agents"
            active={active === 'agents'}
            collapsed={collapsed}
          />

          <SidebarNavItem
            ref={masRef}
            onClick={() => onNavigate('mas')}
            iconSrc={agentsIcon}
            label="Multi Agent Systems"
            active={active === 'mas'}
            collapsed={collapsed}
          />
        </div>
      </nav>

      <div className={collapsed ? 'mt-auto px-2 pb-4' : 'mt-auto px-4 pb-6'}>
        <SidebarFooterButton onClick={() => onNavigate('home')} collapsed={collapsed}>
          Docs
        </SidebarFooterButton>
      </div>
    </aside>
  );
}
