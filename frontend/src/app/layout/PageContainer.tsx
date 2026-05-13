import type { ReactNode } from 'react';

type PageContainerProps = {
  children: ReactNode;
  className?: string;
};

// Renders the page container.
export function PageContainer({ children, className }: PageContainerProps) {
  return <div className={['mx-auto w-full', className].filter(Boolean).join(' ')}>{children}</div>;
}
