import type { ReactNode } from 'react';

type MasTabItem<Key extends string> = {
  key: Key;
  label: string;
};

type MasTabsProps<Key extends string> = {
  tabs: MasTabItem<Key>[];
  activeKey: Key;
  onChange: (key: Key) => void;
  renderPrefix?: (tab: MasTabItem<Key>, active: boolean) => ReactNode;
  scrollable?: boolean;
  wrapperClassName?: string;
  innerClassName?: string;
  minTabWidthClassName?: string;
  buttonClassName?: string;
  activeButtonClassName?: string;
  inactiveButtonClassName?: string;
  labelClassName?: string;
  activeLabelClassName?: string;
  inactiveLabelClassName?: string;
};

export function MasTabs<Key extends string>({
  tabs,
  activeKey,
  onChange,
  renderPrefix,
  scrollable = false,
  wrapperClassName = '',
  innerClassName = '',
  minTabWidthClassName = 'min-w-36',
  buttonClassName = 'flex h-full cursor-pointer items-center px-4 py-2 text-left transition-colors',
  activeButtonClassName = 'bg-slate-50',
  inactiveButtonClassName = 'bg-white hover:bg-slate-50',
  labelClassName = 'text-sm font-semibold',
  activeLabelClassName = 'text-slate-900',
  inactiveLabelClassName = 'text-slate-500',
}: MasTabsProps<Key>) {
  const outerClassName = scrollable
    ? `min-w-0 shrink-0 overflow-x-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden ${wrapperClassName}`.trim()
    : wrapperClassName.trim();

  return (
    <div className={outerClassName}>
      <div className={`flex ${scrollable ? 'min-w-max' : 'w-full'} flex-row items-start p-0 ${innerClassName}`.trim()}>
        {tabs.map((tab) => {
          const active = activeKey === tab.key;

          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => onChange(tab.key)}
              className={[
                buttonClassName,
                minTabWidthClassName,
                active ? activeButtonClassName : inactiveButtonClassName,
              ].join(' ')}
            >
              {renderPrefix ? renderPrefix(tab, active) : null}
              <p
                className={[
                  labelClassName,
                  active ? activeLabelClassName : inactiveLabelClassName,
                ].join(' ')}
              >
                {tab.label}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
