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

  return (
    <div className="min-h-screen bg-white text-black">
      <div className="flex min-h-screen">
        <Sidebar active={active} onNavigate={setActive} />
        <div className="flex-1">
          <TopBar title={title} />
          <main className="p-6">{active === 'agents' ? <AgentsPage /> : <HomePage />}</main>
        </div>
      </div>
    </div>
  );
}

export default App;
