import { useMemo, useState } from 'react';

type MasTracesTabProps = {
  agentNames: string[];
};

function formatAgentName(agentName: string) {
  return agentName
    .replace(/_agent$/, '')
    .replace('esi345', 'ESI3,4,5')
    .replace('esi2', 'ESI2')
    .replace('esi1', 'ESI1')
    .replace('vitals', 'Vitals')
    .replace('doctor', 'Doctor');
}

export default function MasTracesTab({ agentNames }: MasTracesTabProps) {
  const normalizedAgentNames = useMemo(
    () => agentNames.filter((name, index, arr) => arr.indexOf(name) === index),
    [agentNames],
  );

  const [activeAgentName, setActiveAgentName] = useState<string | null>(
    normalizedAgentNames[0] ?? null,
  );

  return (
    <div className="grid h-full w-full grid-cols-5 grid-rows-1">
      <div className="col-span-1 h-full border-r border-slate-300 bg-slate-100/60">
        {normalizedAgentNames.map((agentName) => {
          const active = activeAgentName === agentName;

          return (
            <button
              key={agentName}
              type="button"
              onClick={() => setActiveAgentName(agentName)}
              className={[
                'w-full border-b border-slate-300 p-3 text-left text-sm transition-all duration-150 ease-in-out',
                active
                  ? 'bg-white font-semibold text-slate-900'
                  : 'text-slate-700 hover:bg-slate-50 hover:pl-4 hover:text-slate-900',
              ].join(' ')}
            >
              {formatAgentName(agentName)}
            </button>
          );
        })}
      </div>

      <div className="col-span-4 h-full bg-white p-6">
        <p className="text-sm font-semibold text-slate-900">Selected Agent</p>
        <p className="mt-3 text-base text-slate-700">
          {activeAgentName ? formatAgentName(activeAgentName) : 'No agent selected'}
        </p>
        {activeAgentName ? (
          <p className="mt-2 text-sm text-slate-500">{activeAgentName}</p>
        ) : null}
      </div>
    </div>
  );
}
