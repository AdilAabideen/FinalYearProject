import { useState } from 'react';
import type { NavKey } from './navigation/Sidebar';
import { AppShell } from './layout/AppShell';
import { AgentsPage } from '../features/agents/pages/AgentsPage';
import { SingleAgentsPage } from '../features/agents/pages/SingleAgentPage';
import { MasPage } from '../features/mas/pages/MasPage';

type BackAction = { label?: string; onClick: () => void };
type HeaderOverride = {
  title: string;
  subtitle?: string;
  showSearch?: boolean;
  backAction?: BackAction;
  contentOverflow?: 'auto' | 'hidden';
};

// Renders the app.
function App() {
  const [active, setActive] = useState<NavKey>('agents');
  const [agentsHeaderOverride, setAgentsHeaderOverride] = useState<HeaderOverride | null>(null);
  const [masHeaderOverride, setMasHeaderOverride] = useState<HeaderOverride | null>(null);

  const copy: Record<NavKey, { title: string; subtitle: string }> = {
    single_agent: {
      title: 'Single Agent',
      subtitle: 'Select the Single Agent',
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
    active === 'agents'
      ? (agentsHeaderOverride?.title ?? base.title)
      : active === 'mas'
        ? (masHeaderOverride?.title ?? base.title)
        : base.title;
  const subtitle =
    active === 'agents'
      ? (agentsHeaderOverride?.subtitle ?? base.subtitle)
      : active === 'mas'
        ? (masHeaderOverride?.subtitle ?? base.subtitle)
        : base.subtitle;
  const showSearch =
    active === 'agents'
      ? (agentsHeaderOverride?.showSearch ?? true)
      : active === 'mas'
        ? (masHeaderOverride?.showSearch ?? false)
        : false;
  const backAction =
    active === 'agents'
      ? agentsHeaderOverride?.backAction
      : active === 'mas'
        ? masHeaderOverride?.backAction
        : undefined;
  const contentOverflow =
    active === 'agents'
      ? (agentsHeaderOverride?.contentOverflow ?? 'auto')
      : active === 'mas'
        ? (masHeaderOverride?.contentOverflow ?? 'auto')
        : 'auto';

// Handles navigate.
  function handleNavigate(key: NavKey) {
    setActive(key);
    if (key !== 'agents') setAgentsHeaderOverride(null);
    if (key !== 'mas') setMasHeaderOverride(null);
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
    ) : active === 'single_agent' ? (
      <SingleAgentsPage />
    ) : (
      <MasPage onHeaderChange={setMasHeaderOverride} />
    )}
  </AppShell>
  );
}

export default App;
