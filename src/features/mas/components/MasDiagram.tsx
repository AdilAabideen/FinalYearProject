import { cn } from '../../../shared/lib/cn';
import type { MasCatalogDetail } from '../../../types/mas';
import type { ActiveHandoffEdges, AgentRunningStatus, BoundaryEdgeHighlights } from './MasDetailSplitView';
import { formatMasAgentName } from '../utils/format';

type MasDiagramProps = {
  workflow: MasCatalogDetail;
  agentStatus?: AgentRunningStatus;
  activeHandoffEdges?: ActiveHandoffEdges;
  boundaryEdgeHighlights?: BoundaryEdgeHighlights;
};

type Point = { x: number; y: number };
type BoundaryEdgeState = BoundaryEdgeHighlights['start'];
type HandoffEdgeState = ActiveHandoffEdges[string];
type PositionedAgent = {
  name: string;
  title: string;
  position: Point;
};
type BoundaryNode = {
  key: string;
  label: string;
  position: Point;
};
type StartNode = BoundaryNode & {
  target: Point;
};
type EndNode = BoundaryNode & {
  source: Point;
};

const LINK_STROKE_WIDTH = 3;
const INPUT_OUTPUT_STROKE_WIDTH = 3;

// Handles connector path.
function connectorPath(from: Point, to: Point) {
  return `M ${from.x} ${from.y} L ${to.x} ${to.y}`;
}

// Gets boundary node key.
function getBoundaryNodeKey(type: 'start' | 'end', index: number, total: number) {
  if (total <= 1) return type;
  return `${type}_v${index + 1}`;
}

// Gets boundary stroke class.
function getBoundaryStrokeClass(state: BoundaryEdgeState) {
  if (state === 'active') return 'stroke-green-500';
  if (state === 'visited') return 'stroke-slate-400';
  return 'stroke-slate-200';
}

// Gets handoff stroke class.
function getHandoffStrokeClass(state: HandoffEdgeState) {
  if (state === 'active') return 'stroke-green-500';
  if (state === 'visited') return 'stroke-slate-400';
  return 'stroke-slate-200';
}

// Renders the boundary arrow marker.
function BoundaryArrowMarker() {
  return (
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
  );
}

// Renders the handoff links.
function HandoffLinks({
  links,
  agentPositions,
  activeHandoffEdges,
}: {
  links: Array<{ from: string; to: string }>;
  agentPositions: Record<string, Point>;
  activeHandoffEdges: ActiveHandoffEdges;
}) {
  return (
    <>
      {links.map(({ from, to }) => {
        const fromPosition = agentPositions[from];
        const toPosition = agentPositions[to];
        if (!fromPosition || !toPosition) return null;

        const edgeKey = `${from}->${to}`;
        const edgeStatus = activeHandoffEdges[edgeKey];

        return (
          <path
            key={`${from}-${to}`}
            d={connectorPath(fromPosition, toPosition)}
            fill="none"
            strokeLinecap="round"
            className={cn('transition-colors', getHandoffStrokeClass(edgeStatus))}
            strokeWidth={edgeStatus === 'active' ? LINK_STROKE_WIDTH + 1 : LINK_STROKE_WIDTH}
            vectorEffect="non-scaling-stroke"
          />
        );
      })}
    </>
  );
}

// Renders the boundary links.
function BoundaryLinks({
  nodes,
  type,
  state,
}: {
  nodes: StartNode[] | EndNode[];
  type: 'start' | 'end';
  state: BoundaryEdgeState;
}) {
  return (
    <>
      {nodes.map((node) => (
        <path
          key={node.key}
          d={
            type === 'start'
              ? connectorPath(node.position, (node as StartNode).target)
              : connectorPath((node as EndNode).source, node.position)
          }
          fill="none"
          strokeLinecap="round"
          className={cn('transition-colors', getBoundaryStrokeClass(state))}
          strokeWidth={state === 'active' ? INPUT_OUTPUT_STROKE_WIDTH + 1 : INPUT_OUTPUT_STROKE_WIDTH}
          vectorEffect="non-scaling-stroke"
          markerEnd="url(#mas-boundary-arrow)"
        />
      ))}
    </>
  );
}

// Renders the boundary node badge.
function BoundaryNodeBadge({ node }: { node: BoundaryNode }) {
  return (
    <div
      className="absolute flex h-12 w-28 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-xl bg-PrimaryBlue/90 p-6 text-center text-white shadow-sm"
      style={{ left: `${node.position.x}%`, top: `${node.position.y}%` }}
    >
      <div className="flex items-center justify-center gap-2">
        <p className="truncate text-sm font-semibold text-white">{node.label}</p>
      </div>
    </div>
  );
}

// Renders the agent node.
function AgentNode({
  agent,
  status,
}: {
  agent: PositionedAgent;
  status: AgentRunningStatus[string];
}) {
  return (
    <div
      className={`absolute flex h-36 w-36 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center gap-2 rounded-full border-3 ${status === 'running' ? 'border-green-500' : 'border-PrimaryBlue'} bg-white p-6 text-center shadow-sm`}
      style={{ left: `${agent.position.x}%`, top: `${agent.position.y}%` }}
    >
      <div className="flex items-center justify-center gap-2">
        <span className="h-2 w-2 rounded-full bg-PrimaryBlue" />
        <p className="truncate text-sm font-semibold text-slate-900">{agent.title}</p>
      </div>
      <button
        type="button"
        className="cursor-pointer rounded-[8px] border border-slate-400 px-2 py-1 text-xs font-medium text-slate-600 transition-all ease-in-out hover:bg-slate-200 hover:text-slate-800"
      >
        View Agent
      </button>
    </div>
  );
}

// Renders the MAS diagram.
export function MasDiagram({
  workflow,
  agentStatus = {},
  activeHandoffEdges = {},
  boundaryEdgeHighlights = { start: 'idle', end: 'idle' },
}: MasDiagramProps) {
  const data = workflow;
  const agentPositions = data.agent_positions;

  const agents: PositionedAgent[] = data.participating_agents
    .map((agentName) => ({
      name: agentName,
      title: formatMasAgentName(agentName),
      position: agentPositions[agentName],
    }))
    .filter((agent) => agent.position);

  const startNodes: StartNode[] = data.start_agents
    .map((agentName, index) => {
      const key = getBoundaryNodeKey('start', index, data.start_agents.length);
      const position = agentPositions[key];
      const target = agentPositions[agentName];
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


  const endNodes: EndNode[] = data.finalizing_agents
    .map((agentName, index) => {
      const key = getBoundaryNodeKey('end', index, data.finalizing_agents.length);
      const position = agentPositions[key];
      const source = agentPositions[agentName];
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
          <BoundaryArrowMarker />
        </defs>

        <HandoffLinks
          links={links}
          agentPositions={agentPositions}
          activeHandoffEdges={activeHandoffEdges}
        />
        <BoundaryLinks
          nodes={startNodes}
          type="start"
          state={boundaryEdgeHighlights.start}
        />
        <BoundaryLinks
          nodes={endNodes}
          type="end"
          state={boundaryEdgeHighlights.end}
        />
      </svg>


      {startNodes.map((node) => (
        <BoundaryNodeBadge key={node.key} node={node} />
      ))}

      {endNodes.map((node) => (
        <BoundaryNodeBadge key={node.key} node={node} />
      ))}

      {agents.map((agent) => (
        <AgentNode
          key={agent.name}
          agent={agent}
          status={agentStatus[agent.name]}
        />
      ))}
    </div>
  );
}
