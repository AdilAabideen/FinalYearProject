import { useMemo, useState } from 'react';
import { cn } from '../../lib/cn';
import { formatJson } from '../../lib/formatJson';
import type { AgentCatalogDetail, ToolCatalogItem } from '../../types/agents';
import { Badge } from '../ui/Badge';
import { CodeBlock } from '../ui/CodeBlock';

type AgentDiagramProps = {
  agent: AgentCatalogDetail;
};

type Point = { x: number; y: number };

function getSchemaLabel(schema: Record<string, unknown>) {
  const title = schema.title;
  if (typeof title === 'string' && title.trim().length) return title;

  const ref = schema.$ref;
  if (typeof ref === 'string' && ref.trim().length) return ref.split('/').at(-1) ?? 'Input';

  return 'Input';
}

function computeRadialPositions(count: number): Point[] {
  if (count <= 0) return [];

  const itemsPerRing = 8;
  const ringCount = Math.max(1, Math.ceil(count / itemsPerRing));

  const minRadius = 26;
  const maxRadius = 46;
  const radii = Array.from({ length: ringCount }, (_, ring) => {
    if (ringCount === 1) return 38;
    return minRadius + (ring * (maxRadius - minRadius)) / (ringCount - 1);
  });

  const points: Point[] = [];

  for (let ring = 0; ring < ringCount; ring += 1) {
    const start = ring * itemsPerRing;
    const end = Math.min(count, start + itemsPerRing);
    const ringItems = end - start;
    const radius = radii[ring] ?? 38;

    for (let i = 0; i < ringItems; i += 1) {
      const angle = -Math.PI / 2 + (2 * Math.PI * i) / ringItems;
      points.push({
        x: 50 + radius * Math.cos(angle),
        y: 50 + radius * Math.sin(angle),
      });
    }
  }

  return points;
}

function ToolNode({
  tool,
  active,
  onActiveChange,
}: {
  tool: ToolCatalogItem;
  active: boolean;
  onActiveChange: (active: boolean) => void;
}) {
  return (
      <button
        type="button"
        className={cn(
          'group relative w-44 rounded-2xl border bg-white px-3 py-2 text-left shadow-sm transition focus:outline-none focus:ring-4 focus:ring-PrimaryBlue/20 sm:w-48',
        active ? 'border-PrimaryBlue' : 'border-slate-200 hover:border-PrimaryBlue/70',
      )}
      onMouseEnter={() => onActiveChange(true)}
      onMouseLeave={() => onActiveChange(false)}
      onFocus={() => onActiveChange(true)}
      onBlur={() => onActiveChange(false)}
    >
      <p className="truncate text-xs font-semibold text-slate-900">{tool.name}</p>
      <p className="mt-1 max-h-8 overflow-hidden text-[11px] leading-snug text-slate-600">
        {tool.description || '—'}
      </p>

      <div className="absolute left-1/2 top-full z-20 mt-2 hidden w-80 -translate-x-1/2 rounded-2xl border border-slate-200 bg-white p-3 shadow-lg group-hover:block group-focus-within:block">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">{tool.name}</p>
            {tool.description ? (
              <p className="mt-0.5 text-xs text-slate-600">{tool.description}</p>
            ) : null}
          </div>
          <Badge className="shrink-0 bg-slate-100 text-slate-700 ring-slate-200">Schema</Badge>
        </div>

        <CodeBlock
          code={formatJson(tool.argsSchema)}
          className="mt-3 max-h-56 border-0 bg-slate-50 p-3"
        />
      </div>
    </button>
  );
}

export function AgentDiagram({ agent }: AgentDiagramProps) {
  const [activeToolIndex, setActiveToolIndex] = useState<number | null>(null);

  const positions = useMemo(() => computeRadialPositions(agent.tools.length), [agent.tools.length]);
  const inputLabel = useMemo(() => getSchemaLabel(agent.inputSchema), [agent.inputSchema]);

  return (
    <div className="relative h-full w-full">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0  "
      />
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 100 100"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="agent-diagram-glow" cx="50%" cy="50%" r="60%">
            <stop offset="0%" stopColor="rgb(var(--PrimaryBlue) / 0.10)" />
            <stop offset="70%" stopColor="rgb(var(--PrimaryBlue) / 0.02)" />
            <stop offset="100%" stopColor="rgb(var(--PrimaryBlue) / 0)" />
          </radialGradient>
        </defs>

        <circle cx="50" cy="50" r="36" fill="url(#agent-diagram-glow)" />

        {positions.map((p, i) => (
          <line
            key={`${p.x}-${p.y}`}
            x1={50}
            y1={50}
            x2={p.x}
            y2={p.y}
            className={cn(
              'transition-colors',
              activeToolIndex === i ? 'stroke-PrimaryBlue' : 'stroke-slate-200',
            )}
            strokeWidth={activeToolIndex === i ? 1.4 : 1}
          />
        ))}

        <circle cx="50" cy="50" r="12" className="fill-white stroke-slate-200" strokeWidth={1} />
      </svg>

      <div className="absolute left-1/2 top-1/2 w-56 -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-slate-200 bg-white p-4 text-center shadow-sm">
        <div className="flex items-center justify-center gap-2">
          <span className="h-2 w-2 rounded-full bg-PrimaryBlue" />
          <p className="truncate text-sm font-semibold text-slate-900">{agent.title}</p>
        </div>
        <p className="mt-1 truncate text-xs text-slate-500">{agent.name}</p>

        <div className="mt-3 flex items-center justify-center gap-2">
          <Badge className="bg-PrimaryBlue/10 text-PrimaryBlue ring-PrimaryBlue/20">Input</Badge>
          <p className="truncate text-xs font-medium text-slate-700">{inputLabel}</p>
        </div>
      </div>

      {agent.tools.map((tool, i) => {
        const p = positions[i];
        if (!p) return null;

        return (
          <div
            key={tool.name}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${p.x}%`, top: `${p.y}%` }}
          >
            <ToolNode
              tool={tool}
              active={activeToolIndex === i}
              onActiveChange={(isActive) => setActiveToolIndex(isActive ? i : null)}
            />
          </div>
        );
      })}
    </div>
  );
}
