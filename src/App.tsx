import { useMemo, useState } from 'react';
import { Sidebar, type NavKey } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { AgentsPage } from './pages/AgentsPage';
import { HomePage } from './pages/HomePage';

function App() {
  const [active, setActive] = useState<NavKey>('agents');

  const title = useMemo(() => {
    switch (active) {
      case 'home':
        return 'Home';
      case 'agents':
        return 'Agents';
    }
  }, [active]);

  const subtitle = useMemo(() => {
    switch (active) {
      case 'home':
        return 'Overview and quick links';
      case 'agents':
        return 'Manage and launch triage agents';
    }
  }, [active]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        <Sidebar active={active} onNavigate={setActive} />
        <div className="flex-1">
          <TopBar title={title} subtitle={subtitle} showSearch={active === 'agents'} />
          <main className="p-6">
            <div className="mx-auto w-full max-w-6xl">
              {active === 'agents' ? <AgentsPage /> : <HomePage />}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
