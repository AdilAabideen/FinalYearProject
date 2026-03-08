import type { ReactNode } from 'react';
import { Sidebar, type NavKey } from '../Sidebar';
import { TopBar } from '../TopBar';
import { PageContainer } from './PageContainer';

type BackAction = {
  label?: string;
  onClick: () => void;
};

type AppShellProps = {
  activeNav: NavKey;
  onNavigate: (key: NavKey) => void;
  title: string;
  subtitle?: string;
  showSearch?: boolean;
  backAction?: BackAction;
  contentOverflow?: 'auto' | 'hidden';
  children: ReactNode;
};

export function AppShell({
  activeNav,
  onNavigate,
  title,
  subtitle,
  showSearch,
  backAction,
  contentOverflow = 'auto',
  children,
}: AppShellProps) {
  return (
    <div className="h-screen overflow-hidden bg-slate-50 text-slate-900">
      <div className="flex h-full">
        <Sidebar active={activeNav} onNavigate={onNavigate} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar title={title} subtitle={subtitle} showSearch={showSearch} backAction={backAction} />
          <main
            className={[
              'flex-1 min-h-0 p-0',
              contentOverflow === 'hidden' ? 'overflow-hidden' : 'overflow-auto',
            ].join(' ')}
          >
            <PageContainer className="h-full">{children}</PageContainer>
          </main>
        </div>
      </div>
    </div>
  );
}
