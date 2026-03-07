import agentsIcon from '../assets/figma/icon-agents.png';
import homeIcon from '../assets/figma/icon-home.png';
import logoPng from '../assets/figma/logo.png';

export type NavKey = 'home' | 'agents';

type SidebarProps = {
  active: NavKey;
  onNavigate: (key: NavKey) => void;
};

export function Sidebar({ active, onNavigate }: SidebarProps) {
  const navItemBase =
    'group relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white';
  const navItemActive =
    'bg-slate-50 text-slate-900 shadow-sm ring-1 ring-slate-200/60 before:absolute before:left-1 before:top-2 before:bottom-2 before:w-1 before:rounded-full before:bg-teal-600';
  const navItemInactive = 'text-slate-700 hover:bg-slate-50 hover:text-slate-900';

  const iconBase = 'h-5 w-5 shrink-0 object-contain transition-opacity';
  const iconActive = 'opacity-100';
  const iconInactive = 'opacity-70 group-hover:opacity-100';

  return (
    <aside className="flex w-64 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-3 px-4 py-5">
        <img alt="" src={logoPng} className="h-8 w-10 rounded-md" draggable={false} />
        <div className="leading-tight">
          <div className="text-lg font-semibold text-slate-900">IntelliTriage</div>
          <div className="text-xs text-slate-500">Emergency triage workspace</div>
        </div>
      </div>

      <nav className="px-4" aria-label="Primary">
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => onNavigate('home')}
            aria-current={active === 'home' ? 'page' : undefined}
            className={[navItemBase, active === 'home' ? navItemActive : navItemInactive].join(' ')}
          >
            <img
              alt=""
              src={homeIcon}
              className={[iconBase, active === 'home' ? iconActive : iconInactive].join(' ')}
              draggable={false}
            />
            <span>Home</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('agents')}
            aria-current={active === 'agents' ? 'page' : undefined}
            className={[
              navItemBase,
              active === 'agents' ? navItemActive : navItemInactive,
            ].join(' ')}
          >
            <img
              alt=""
              src={agentsIcon}
              className={[iconBase, active === 'agents' ? iconActive : iconInactive].join(' ')}
              draggable={false}
            />
            <span>Agents</span>
          </button>
        </div>
      </nav>

      <div className="mt-auto px-4 pb-6">
        <button
          type="button"
          className="w-full rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
          onClick={() => onNavigate('home')}
        >
          Docs
        </button>
      </div>
    </aside>
  );
}
