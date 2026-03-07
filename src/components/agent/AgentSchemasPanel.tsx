import { formatJson } from '../../lib/formatJson';
import type { AgentCatalogDetail } from '../../types/agents';
import { Badge } from '../ui/Badge';
import { CodeBlock } from '../ui/CodeBlock';
import { StatChip } from '../ui/StatChip';

type AgentSchemasPanelProps = {
  agent: AgentCatalogDetail;
};

export function AgentSchemasPanel({ agent }: AgentSchemasPanelProps) {
  return (
    <div className="flex min-h-0 flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="bg-slate-100 text-slate-700 ring-slate-200">Agent</Badge>
          <span className="font-mono text-xs text-slate-600">{agent.name}</span>
        </div>
        <StatChip value={agent.tools.length} label="Tools" />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-slate-900">Input Schema</h3>
          <span className="text-xs text-slate-500">Pydantic JSON Schema</span>
        </div>
        <CodeBlock code={formatJson(agent.inputSchema)} className="max-h-80" />
      </div>

      <div className="min-h-0 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-slate-900">Tools</h3>
          <span className="text-xs text-slate-500">Expand to view args schema</span>
        </div>

        <div className="min-h-0 space-y-3 overflow-auto pr-1">
          {agent.tools.map((tool) => (
            <details
              key={tool.name}
              className="group rounded-2xl border border-slate-200 bg-white shadow-sm open:shadow-md"
            >
              <summary className="flex cursor-pointer list-none items-start justify-between gap-4 p-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900">{tool.name}</p>
                  <p className="mt-1 text-sm text-slate-600">{tool.description || '—'}</p>
                </div>
                <span className="mt-0.5 shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                  Args schema
                </span>
              </summary>
              <div className="border-t border-slate-200 p-4">
                <CodeBlock code={formatJson(tool.argsSchema)} className="max-h-72" />
              </div>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
}

