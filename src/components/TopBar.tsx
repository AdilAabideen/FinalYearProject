import { TextInput } from './ui/TextInput';

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
          <TextInput
            srLabel="Search agents"
            id="agent-search"
            type="text"
            disabled
            placeholder="Search agents (coming soon)"
            className="w-72"
          />
        </div>
      ) : null}
    </header>
  );
}
