import { useRef, type KeyboardEvent } from 'react';
import { cn } from '../lib/cn';

type TabItem<T extends string> = {
  key: T;
  label: string;
};

type SegmentedTabsProps<T extends string> = {
  idBase: string;
  tabs: readonly TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
  className?: string;
};

// Renders the segmented tabs.
export function SegmentedTabs<T extends string>({
  idBase,
  tabs,
  value,
  onChange,
  ariaLabel,
  className,
}: SegmentedTabsProps<T>) {
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

// Handles tab ID.
  function tabId(key: T) {
    return `${idBase}-tab-${key}`;
  }

// Handles panel ID.
  function panelId(key: T) {
    return `${idBase}-panel-${key}`;
  }

// Handles key down.
  function handleKeyDown(key: T) {
    return (e: KeyboardEvent<HTMLButtonElement>) => {
      const currentIndex = tabs.findIndex((tab) => tab.key === key);
      if (currentIndex < 0) return;

      let nextIndex = currentIndex;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nextIndex = (currentIndex + 1) % tabs.length;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      if (e.key === 'Home') nextIndex = 0;
      if (e.key === 'End') nextIndex = tabs.length - 1;

      if (nextIndex === currentIndex) return;

      e.preventDefault();
      const nextKey = tabs[nextIndex]?.key ?? tabs[0]?.key;
      if (!nextKey) return;

      onChange(nextKey);
      tabRefs.current[nextKey]?.focus();
    };
  }

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        `grid gap-1 rounded-xl bg-slate-100 p-1 ring-1 ring-slate-200`,
        className,
      )}
      style={{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }}
    >
      {tabs.map((tab) => {
        const selected = tab.key === value;
        return (
          <button
            key={tab.key}
            ref={(node) => {
              tabRefs.current[tab.key] = node;
            }}
            id={tabId(tab.key)}
            role="tab"
            type="button"
            tabIndex={selected ? 0 : -1}
            aria-selected={selected}
            aria-controls={panelId(tab.key)}
            onClick={() => onChange(tab.key)}
            onKeyDown={handleKeyDown(tab.key)}
            className={cn(
              'inline-flex items-center justify-center rounded-lg px-3 py-2 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white',
              selected
                ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200'
                : 'text-slate-600 hover:bg-white/70 hover:text-slate-900',
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

