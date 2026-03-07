import agentsIcon from '../assets/figma/icon-agents.png';
import homeIcon from '../assets/figma/icon-home.png';
import logoPng from '../assets/figma/logo.png';

export type NavKey = 'home' | 'agents';

type SidebarProps = {
  active: NavKey;
  onNavigate: (key: NavKey) => void;
};

export function Sidebar({ active, onNavigate }: SidebarProps) {
  return (
    <aside className="flex w-64 flex-col border-r border-neutral-200 bg-neutral-100">
      <div className="flex items-center gap-2 px-4 py-5">
        <img alt="" src={logoPng} className="h-10 w-12" draggable={false} />
        <span className="text-2xl font-medium mt-1">IntelliTriage</span>
      </div>

      <nav className="px-4" aria-label="Primary">
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => onNavigate('home')}
            className={[
              'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-black transition-colors',
              active === 'home' ? 'bg-white shadow-sm' : 'hover:bg-white/60',
            ].join(' ')}
          >
            <img alt="" src={homeIcon} className="h-5 w-5 object-contain" draggable={false} />
            <span>Home</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('agents')}
            className={[
              'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-black transition-colors',
              active === 'agents' ? 'bg-white shadow-sm' : 'hover:bg-white/60',
            ].join(' ')}
          >
            <img alt="" src={agentsIcon} className="h-5 w-5 object-contain mb-[2px]" draggable={false} />
            <span className="text-md mt-[2px] ">Agents</span>
          </button>
        </div>
      </nav>

      <div className="mt-auto px-4 pb-6">
        <button
          type="button"
          className="text-sm text-black hover:underline"
          onClick={() => onNavigate('home')}
        >
          Docs
        </button>
      </div>
    </aside>
  );
}
