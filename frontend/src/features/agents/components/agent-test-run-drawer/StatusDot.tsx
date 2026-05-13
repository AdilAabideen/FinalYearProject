// Renders the status dot.
export function StatusDot({ status }: { status: 'pending' | 'running' | 'passed' | 'failed' }) {
  const color =
    status === 'running'
      ? 'bg-orange-400'
      : status === 'passed'
        ? 'bg-emerald-500'
        : status === 'failed'
          ? 'bg-rose-500'
          : 'bg-slate-300';
  return <span className={`inline-flex h-2.5 w-2.5 rounded-full ${color}`} />;
}
