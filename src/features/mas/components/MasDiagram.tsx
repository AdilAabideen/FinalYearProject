import { cn } from '../../../shared/lib/cn';
import type { MasCatalogDetail } from '../../../types/mas';

type MasDiagramProps = {
  workflow: MasCatalogDetail;
};

type Point = { x: number; y: number };

const LINK_STROKE_WIDTH = 3;
const INPUT_OUTPUT_STROKE_WIDTH = 4;

const agent_positions_map: Record<string, Point> = {
  esi1_agent: { x: 14, y: 52 },
  esi2_agent: { x: 30, y: 82 },
  esi345_agent: { x: 60, y: 70 },
  vitals_agent: { x: 84, y: 76 },
  doctor_agent: { x: 67, y: 18 },
  start_v1: { x: 14, y: 10 },
  start_v2: { x: 84, y: 10 },
  end: { x: 70, y: 90 },
};



function connectorPath(from: Point, to: Point) {
  return `M ${from.x} ${from.y} L ${to.x} ${to.y}`;
}

function getBoundaryNodeKey(type: 'start' | 'end', index: number, total: number) {
  if (total <= 1) return type;
  return `${type}_v${index + 1}`;
}

function formatAgentTitle(agentName: string) {
  return agentName
    .replace(/_agent$/, '')
    .replace('esi345', 'ESI3,4,5')
    .replace('esi2', 'ESI2')
    .replace('esi1', 'ESI1')
    .replace('vitals', 'Vitals')
    .replace('doctor', 'Doctor');
}

export function MasDiagram({ workflow }: MasDiagramProps) {
  const data = workflow 

  const agents = data.participating_agents
    .map((agentName) => ({
      name: agentName,
      title: formatAgentTitle(agentName),
      position: agent_positions_map[agentName],
    }))
    .filter((agent) => agent.position);

  const startNodes = data.start_agents
    .map((agentName, index) => {
      const key = getBoundaryNodeKey('start', index, data.start_agents.length);
      const position = agent_positions_map[key];
      const target = agent_positions_map[agentName];
      if (!position || !target) return null;

      return {
        key,
        label: 'START',
        position,
        target,
      };
    })
    .filter(
      (node): node is { key: string; label: string; position: Point; target: Point } =>
        Boolean(node),
    );

  const endNodes = data.finalizing_agents
    .map((agentName, index) => {
      const key = getBoundaryNodeKey('end', index, data.finalizing_agents.length);
      const position = agent_positions_map[key];
      const source = agent_positions_map[agentName];
      if (!position || !source) return null;

      return {
        key,
        label: 'END',
        position,
        source,
      };
    })
    .filter(
      (node): node is { key: string; label: string; position: Point; source: Point } =>
        Boolean(node),
    );

  const links = Object.entries(data.allowed_handoffs).flatMap(([from, targets]) =>
    targets.map((to) => ({ from, to })),
  );

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
        <defs>
          <marker
            id="mas-boundary-arrow"
            markerWidth="6"
            markerHeight="6"
            refX="5"
            refY="3"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <path d="M 0 0 L 6 3 L 0 6 z" className="fill-slate-200" />
          </marker>
        </defs>

        {links.map(({ from, to }) => {
          const fromPosition = agent_positions_map[from];
          const toPosition = agent_positions_map[to];
          if (!fromPosition || !toPosition) return null;

          return (
            <path
              key={`${from}-${to}`}
              d={connectorPath(fromPosition, toPosition)}
              fill="none"
              strokeLinecap="round"
              className={cn('transition-colors stroke-slate-300')}
              strokeWidth={LINK_STROKE_WIDTH}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}

        {startNodes.map((node) => (
          <path
            key={node.key}
            d={connectorPath(node.position, node.target)}
            fill="none"
            strokeLinecap="round"
            className={cn('transition-colors stroke-slate-200')}
            strokeWidth={INPUT_OUTPUT_STROKE_WIDTH}
            vectorEffect="non-scaling-stroke"
            markerEnd="url(#mas-boundary-arrow)"
          />
        ))}

        {endNodes.map((node) => (
          <path
            key={node.key}
            d={connectorPath(node.source, node.position)}
            fill="none"
            strokeLinecap="round"
            className={cn('transition-colors stroke-slate-200')}
            strokeWidth={INPUT_OUTPUT_STROKE_WIDTH}
            vectorEffect="non-scaling-stroke"
            markerEnd="url(#mas-boundary-arrow)"
          />
        ))}
      </svg>

      <div className="absolute right-4 top-4 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm">
        {data.metadata.name}
      </div>

      {startNodes.map((node) => (
        <div
          key={node.key}
          className="absolute flex h-12 w-28 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-xl bg-PrimaryBlue/90 p-6 text-center text-white shadow-sm"
          style={{ left: `${node.position.x}%`, top: `${node.position.y}%` }}
        >
          <div className="flex items-center justify-center gap-2">
            <p className="truncate text-sm font-semibold text-white">{node.label}</p>
          </div>
        </div>
      ))}

      {endNodes.map((node) => (
        <div
          key={node.key}
          className="absolute flex h-12 w-28 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-xl bg-PrimaryBlue/90 p-6 text-center text-white shadow-sm"
          style={{ left: `${node.position.x}%`, top: `${node.position.y}%` }}
        >
          <div className="flex items-center justify-center gap-2">
            <p className="truncate text-sm font-semibold text-white">{node.label}</p>
          </div>
        </div>
      ))}

      {agents.map((agent) => (
        <div
          key={agent.name}
          className="absolute flex h-36 w-36 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center gap-2 rounded-full border-2 border-PrimaryBlue bg-white p-6 text-center shadow-sm"
          style={{ left: `${agent.position.x}%`, top: `${agent.position.y}%` }}
        >
          <div className="flex items-center justify-center gap-2">
            <span className="h-2 w-2 rounded-full bg-PrimaryBlue" />
            <p className="truncate text-sm font-semibold text-slate-900">{agent.title}</p>
          </div>
          <button
            type="button"
            className="rounded-[8px] border cursor-pointer border-slate-400  px-2 py-1 text-xs font-medium text-slate-600 transition-all ease-in-out hover:bg-slate-200 hover:text-slate-800"
          >
            View Agent
          </button>
        </div>
      ))}
    </div>
  );
}
