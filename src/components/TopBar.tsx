type TopBarProps = {
  title: string;
  subtitle?: string;
  showSearch?: boolean;
};

export function TopBar({ title, subtitle, showSearch }: TopBarProps) {
  return (
    <header className="flex min-h-16 items-center justify-between gap-6 border-b border-slate-200 bg-white px-6 py-4">
      <div className="min-w-0">
        <h1 className="truncate text-2xl font-semibold text-slate-900">{title}</h1>
        {subtitle ? <p className="mt-0.5 truncate text-sm text-slate-500">{subtitle}</p> : null}
      </div>

      {showSearch ? (
        <div className="hidden sm:block">
          <label className="sr-only" htmlFor="agent-search">
            Search agents
          </label>
          <input
            id="agent-search"
            type="text"
            disabled
            placeholder="Search agents (coming soon)"
            className="w-72 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700 placeholder:text-slate-400 shadow-sm disabled:cursor-not-allowed disabled:opacity-70"
          />
        </div>
      ) : null}
    </header>
  );
}
