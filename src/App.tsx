import { useState } from 'react';
import type { NavKey } from './components/Sidebar';
import { AppShell } from './components/layout/AppShell';
import { AgentsPage } from './pages/AgentsPage';
import { HomePage } from './pages/HomePage';

function App() {
  const [active, setActive] = useState<NavKey>('agents');

  const copy: Record<NavKey, { title: string; subtitle: string }> = {
    home: {
      title: 'Home',
      subtitle: 'Overview and quick links',
    },
    agents: {
      title: 'Available Agents',
      subtitle: 'Select an agent to view its tools and test cases and Test them with test Cases',
    },
  };

  const { title, subtitle } = copy[active];

  return (
    <AppShell
      activeNav={active}
      onNavigate={setActive}
      title={title}
      subtitle={subtitle}
      showSearch={active === 'agents'}
    >
      {active === 'agents' ? <AgentsPage /> : <HomePage />}
    </AppShell>
  );
}

export default App;
