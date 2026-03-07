import type { ReactNode } from 'react';
import { Sidebar, type NavKey } from '../Sidebar';
import { TopBar } from '../TopBar';
import { PageContainer } from './PageContainer';

type AppShellProps = {
  activeNav: NavKey;
  onNavigate: (key: NavKey) => void;
  title: string;
  subtitle?: string;
  showSearch?: boolean;
  children: ReactNode;
};

export function AppShell({
  activeNav,
  onNavigate,
  title,
  subtitle,
  showSearch,
  children,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        <Sidebar active={activeNav} onNavigate={onNavigate} />
        <div className="flex-1">
          <TopBar title={title} subtitle={subtitle} showSearch={showSearch} />
          <main className="p-6">
            <PageContainer>{children}</PageContainer>
          </main>
        </div>
      </div>
    </div>
  );
}

