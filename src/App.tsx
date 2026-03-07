import { useState } from 'react';
import type { NavKey } from './components/Sidebar';
import { AppShell } from './components/layout/AppShell';
import { AgentsPage } from './pages/AgentsPage';
import { HomePage } from './pages/HomePage';

type HeaderOverride = { title: string; subtitle?: string; showSearch?: boolean };

function App() {
  const [active, setActive] = useState<NavKey>('agents');
  const [agentsHeaderOverride, setAgentsHeaderOverride] = useState<HeaderOverride | null>(null);

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

  const base = copy[active];
  const title =
    active === 'agents' && agentsHeaderOverride ? agentsHeaderOverride.title : base.title;
  const subtitle =
    active === 'agents' && agentsHeaderOverride ? agentsHeaderOverride.subtitle : base.subtitle;
  const showSearch =
    active === 'agents' ? (agentsHeaderOverride?.showSearch ?? true) : false;

  function handleNavigate(key: NavKey) {
    setActive(key);
    if (key !== 'agents') setAgentsHeaderOverride(null);
  }

  return (
    <AppShell
      activeNav={active}
      onNavigate={handleNavigate}
      title={title}
      subtitle={subtitle}
      showSearch={showSearch}
    >
      {active === 'agents' ? <AgentsPage onHeaderChange={setAgentsHeaderOverride} /> : <HomePage />}
    </AppShell>
  );
}

export default App;
