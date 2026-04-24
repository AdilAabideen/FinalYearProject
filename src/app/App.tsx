import { useState } from 'react';
import type { NavKey } from './navigation/Sidebar';
import { AppShell } from './layout/AppShell';
import { AgentsPage } from '../features/agents/pages/AgentsPage';
import { HomePage } from '../features/home/pages/HomePage';
import { MasPage } from '../features/mas/pages/MasPage';

type BackAction = { label?: string; onClick: () => void };
type HeaderOverride = {
  title: string;
  subtitle?: string;
  showSearch?: boolean;
  backAction?: BackAction;
  contentOverflow?: 'auto' | 'hidden';
};

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
    mas: {
      title: 'Multi Agent Systems',
      subtitle: 'Design and inspect orchestrated workflows across collaborating agents',
    },
  };

  const base = copy[active];
  const title =
    active === 'agents' && agentsHeaderOverride ? agentsHeaderOverride.title : base.title;
  const subtitle =
    active === 'agents' && agentsHeaderOverride ? agentsHeaderOverride.subtitle : base.subtitle;
  const showSearch =
    active === 'agents' ? (agentsHeaderOverride?.showSearch ?? true) : false;
  const backAction = active === 'agents' ? agentsHeaderOverride?.backAction : undefined;
  const contentOverflow =
    active === 'agents' ? (agentsHeaderOverride?.contentOverflow ?? 'auto') : 'auto';

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
      backAction={backAction}
      contentOverflow={contentOverflow}
    >
      {active === 'agents' ? (
        <AgentsPage onHeaderChange={setAgentsHeaderOverride} />
      ) : active === 'mas' ? (
        <MasPage />
      ) : (
        <HomePage />
      )}
    </AppShell>
  );
}

export default App;
