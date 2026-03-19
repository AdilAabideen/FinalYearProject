import { TextInput } from '../../shared/ui/TextInput';

type BackAction = {
  label?: string;
  onClick: () => void;
};

type TopBarProps = {
  title: string;
  subtitle?: string;
  showSearch?: boolean;
  backAction?: BackAction;
};

export function TopBar({ title, subtitle, showSearch, backAction }: TopBarProps) {
  return (
    <header className="flex min-h-16 items-center justify-between gap-6 border-b border-slate-200 bg-white px-6 py-4">
      <div className="flex min-w-0 items-center gap-3">
        

        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold text-slate-900">{title}</h1>
          {subtitle ? <p className="mt-0.5 truncate text-sm text-slate-500">{subtitle}</p> : null}
        </div>
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
      {backAction ? (
          <button
            type="button"
            onClick={backAction.onClick}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 20 20"
              className="h-4 w-4 text-slate-700"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M12.707 15.707a1 1 0 01-1.414 0l-5-5a1 1 0 010-1.414l5-5a1 1 0 111.414 1.414L8.414 9H16a1 1 0 110 2H8.414l4.293 4.293a1 1 0 010 1.414z"
                clipRule="evenodd"
              />
            </svg>
            <span>{backAction.label ?? 'Back to agents'}</span>
          </button>
        ) : null}
    </header>
  );
}
