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
};

export function Sidebar({ active, onNavigate }: SidebarProps) {
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
    <aside className="flex w-64 flex-col border-r border-slate-200 bg-white">
      <SidebarBrand />

      <nav className="px-4" aria-label="Primary">
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
          />

          <SidebarNavItem
            ref={agentsRef}
            onClick={() => onNavigate('agents')}
            iconSrc={agentsIcon}
            label="Agents"
            active={active === 'agents'}
          />

          <SidebarNavItem
            ref={masRef}
            onClick={() => onNavigate('mas')}
            iconSrc={agentsIcon}
            label="Multi Agent Systems"
            active={active === 'mas'}
          />
        </div>
      </nav>

      <div className="mt-auto px-4 pb-6">
        <SidebarFooterButton onClick={() => onNavigate('home')}>Docs</SidebarFooterButton>
      </div>
    </aside>
  );
}
