import { useState } from 'react';
import type { AgentCatalogDetail } from '../../types/agents';
import { AgentInputForm } from './AgentInputForm';

type RunAgentTabProps = {
  agent: AgentCatalogDetail;
};

export default function RunAgentTab({ agent }: RunAgentTabProps) {
  const [value, setValue] = useState<Record<string, unknown>>({});

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 pt-2 h-full">
      <div>
        <p className="mt-1 text-md text-slate-600">
          Select tools and provide inputs to run this agent.
        </p>
      </div>

      <div className="mt-4">
        <AgentInputForm schema={agent.inputSchema} value={value} onChange={setValue} />
      </div>

      <div className="mt-6 flex items-center justify-end">
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-xl bg-PrimaryBlue px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-PrimaryBlue/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        >
          Run Agent
        </button>
      </div>

    </div>
  );
}
