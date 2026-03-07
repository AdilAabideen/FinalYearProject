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

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function curvedConnectorPath(from: Point, to: Point, curve: number) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.hypot(dx, dy) || 1;

  const px = -dy / dist;
  const py = dx / dist;

  const c1 = {
    x: from.x + dx * 0.28 + px * curve,
    y: from.y + dy * 0.28 + py * curve,
  };

  const c2 = {
    x: from.x + dx * 0.72 + px * curve,
    y: from.y + dy * 0.72 + py * curve,
  };

  return `M ${from.x} ${from.y} C ${c1.x} ${c1.y} ${c2.x} ${c2.y} ${to.x} ${to.y}`;
}

function ConvertToolName(toolName: string) {
  return toolName
    .replace(/_/g, ' ')
    .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1));

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
        'group relative w-52 rounded-xl z-10 border border-PrimaryBlue bg-white px-3 py-2 text-center shadow-sm transition-all focus:outline-none focus:ring-4 focus:ring-PrimaryBlue/20 sm:w-56 hover:border-2',
        active && 'border-2',
      )}
      onMouseEnter={() => onActiveChange(true)}
      onMouseLeave={() => onActiveChange(false)}
      onFocus={() => onActiveChange(true)}
      onBlur={() => onActiveChange(false)}
    >
      <p className="truncate text-xs font-semibold text-slate-900">{ConvertToolName(tool.name)}</p>
      <p className="mt-1 max-h-9 overflow-hidden text-[11px] ml-0 leading-snug text-slate-600">
        {(() => {
          const sentences = tool.description.split(/[.!?]+/).filter(s => s.trim());
          const firstOne = sentences.slice(0, 1).join('. ').trim();
          const words = firstOne.split(/\s+/);
          if (words.length > 15) {
            return words.slice(0, 15).join(' ') + '...';
          }
          return firstOne + (sentences.length > 1 ? '...' : '');
        })()}
      </p>

      <div className="absolute left-1/2 top-full z-20 mt-2 hidden w-80 -translate-x-1/2 rounded-2xl border border-slate-200 bg-white p-3 shadow-lg group-hover:block group-focus-within:block">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm text-left ml-0 font-semibold text-slate-900">{ConvertToolName(tool.name)}</p>
            {tool.description ? (
              <p className="mt-0.5 text-left ml-0 text-xs text-slate-600">
                {(() => {
                  const sentences = tool.description.split(/[.!?]+/).filter(s => s.trim());
                  const firstTwo = sentences.slice(0, 2).join('. ').trim();
                  const words = firstTwo.split(/\s+/);
                  if (words.length > 25) {
                    return words.slice(0, 25).join(' ') + '...';
                  }
                  return firstTwo + (sentences.length > 2 ? '...' : '');
                })()}
              </p>
            ) : null}
          </div>
          <Badge className="shrink-0  ring-slate-200 bg-PrimaryBlue/10 text-PrimaryBlue">Schema</Badge>
        </div>

        <CodeBlock
          code={formatJson(tool.argsSchema)}
          className="mt-3 max-h-56 border-0 bg-slate-50 p-1 text-left ml-0"
        />
      </div>
    </button>
  );
}

export function AgentDiagram({ agent }: AgentDiagramProps) {
  const [activeToolIndex, setActiveToolIndex] = useState<number | null>(null);

  const positions = useMemo(
    () =>
      computeRadialPositions(agent.tools.length).map((p) => ({
        x: clamp(p.x, 10, 90),
        y: clamp(p.y, 10, 90),
      })),
    [agent.tools.length],
  );
  const inputLabel = useMemo(() => getSchemaLabel(agent.inputSchema), [agent.inputSchema]);

  return (
    <div className="relative h-full w-full">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-slate-50 [background-image:radial-gradient(circle_at_1px_1px,rgba(148,163,184,0.35)_1px,transparent_0)] [background-size:18px_18px]"
      />
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {positions.map((p, i) => {
          const dist = Math.hypot(p.x - 50, p.y - 50) || 1;
          const curve = (i % 2 === 0 ? 1 : -1) * clamp(8 - dist / 7, 2.5, 6);
          const d = curvedConnectorPath({ x: 50, y: 50 }, p, curve);

          return (
            <path
              key={`${p.x}-${p.y}`}
              d={d}
              fill="none"
              strokeLinecap="round"
              className={cn(
                'transition-colors',
                activeToolIndex === i ? 'stroke-PrimaryBlue' : 'stroke-slate-400',
              )}
              strokeWidth={activeToolIndex === i ? 1.2 : 0.8}
            />
          );
        })}
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
