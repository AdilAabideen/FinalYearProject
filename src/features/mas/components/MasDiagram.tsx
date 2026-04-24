import { cn } from '../../../shared/lib/cn';
import { Badge } from '../../../shared/ui/Badge';

type MasDiagramProps = {
    workflowName: string;
};

type Point = { x: number; y: number };

const LINK_STROKE_WIDTH = 6;
const INPUT_OUTPUT_STROKE_WIDTH = 6;

const agent_positions_map: Record<string, Point> = {
    esi1_agent: { x: 14, y: 52 },
    esi2_agent: { x: 30, y: 82 },
    esi345_agent: { x: 60, y: 70 },
    vitals_agent: { x: 84, y: 76 },
    doctor_agent: { x: 67, y: 18 },
    start_v1: {x:14, y:10},
    start_v2: {x:84, y:10},
    end: {x:70, y:90}
};

const mock_data = {
    metadata: {
        workflow_id: 'esi_swarm_v1',
        name: 'ESI Swarm V1',
        version: '1.0.0',
        description:
            'Constrained multi-agent ESI workflow with parallel ESI1 and vitals starts, acuity handoffs through ESI2/ESI345, and doctor finalization.',
    },
    participating_agents: [
        'esi1_agent',
        'esi2_agent',
        'esi345_agent',
        'vitals_agent',
        'doctor_agent',
    ],
    start_agents: ['esi1_agent', 'vitals_agent'],
    finalizing_agents: ['doctor_agent'],
    allowed_handoffs: {
        esi1_agent: ['esi2_agent', 'doctor_agent'],
        esi2_agent: ['esi345_agent', 'doctor_agent'],
        esi345_agent: ['doctor_agent'],
        vitals_agent: ['doctor_agent'],
        doctor_agent: [],
    },
    sources: {
        acuity: {
            source_id: 'acuity',
            name: 'Acuity Branch',
            agent_names: ['esi1_agent', 'esi2_agent', 'esi345_agent'],
            description: 'The main ESI acuity decision pathway.',
            metadata: {
                branch_type: 'clinical_acuity',
            },
        },
        vitals: {
            source_id: 'vitals',
            name: 'Vitals Branch',
            agent_names: ['vitals_agent'],
            description: 'The vitals-only parallel support branch.',
            metadata: {
                branch_type: 'physiologic_support',
            },
        },
    },
    gates: {
        doctor_gate: {
            gate_id: 'doctor_gate',
            name: 'Doctor Gate',
            description:
                'Waits until both the acuity branch and vitals branch have handed off before doctor finalization.',
            required_sources: ['acuity', 'vitals'],
            incoming_from: [],
            target_node: 'doctor_agent',
            metadata: {
                gate_type: 'readiness_gate',
                ready_rule: 'requires_required_sources_to_handoff_to_target',
                terminal_when_not_ready: true,
            },
        },
    },
    agent_metadata: {
        esi1_agent: {
            role: 'acuity',
            stage: 'decision_point_a',
            can_handoff: true,
            can_finalize: false,
        },
        esi2_agent: {
            role: 'acuity',
            stage: 'decision_point_b',
            can_handoff: true,
            can_finalize: false,
        },
        esi345_agent: {
            role: 'acuity',
            stage: 'decision_point_c',
            can_handoff: true,
            can_finalize: false,
        },
        vitals_agent: {
            role: 'vitals',
            stage: 'parallel_support',
            can_handoff: true,
            can_finalize: false,
        },
        doctor_agent: {
            role: 'supervisor',
            stage: 'final_review',
            can_handoff: false,
            can_finalize: true,
        },
    },
    workflow_metadata: {
        workflow_family: 'esi_swarm',
        execution_model: 'constrained_swarm',
        parallel_start: true,
        doctor_gate_id: 'doctor_gate',
    },
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

export function MasDiagram({ workflowName }: MasDiagramProps) {
    const agents = mock_data.participating_agents
        .map((agentName) => ({
            name: agentName,
            title: formatAgentTitle(agentName),
            position: agent_positions_map[agentName],
        }))
        .filter((agent) => agent.position);

    const startNodes = mock_data.start_agents
        .map((agentName, index) => {
            const key = getBoundaryNodeKey('start', index, mock_data.start_agents.length);
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
        .filter((node): node is { key: string; label: string; position: Point; target: Point } => Boolean(node));

    const endNodes = mock_data.finalizing_agents
        .map((agentName, index) => {
            const key = getBoundaryNodeKey('end', index, mock_data.finalizing_agents.length);
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
        .filter((node): node is { key: string; label: string; position: Point; source: Point } => Boolean(node));

    const links = Object.entries(mock_data.allowed_handoffs).flatMap(([from, targets]) =>
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
                        className={cn('transition-colors stroke-slate-300')}
                        strokeWidth={INPUT_OUTPUT_STROKE_WIDTH}
                        vectorEffect="non-scaling-stroke"
                    />
                ))}

                {endNodes.map((node) => (
                    <path
                        key={node.key}
                        d={connectorPath(node.source, node.position)}
                        fill="none"
                        strokeLinecap="round"
                        className={cn('transition-colors stroke-slate-300')}
                        strokeWidth={INPUT_OUTPUT_STROKE_WIDTH}
                        vectorEffect="non-scaling-stroke"
                    />
                ))}
            </svg>

            <div className="absolute right-4 top-4 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm">
                {workflowName}
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
                    className="absolute flex h-36 w-36 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full border-[3px] border-PrimaryBlue bg-white p-6 text-center shadow-sm gap-2"
                    style={{ left: `${agent.position.x}%`, top: `${agent.position.y}%` }}
                >
                    <div className="flex items-center justify-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-PrimaryBlue" />
                        <p className="truncate text-sm font-semibold text-slate-900">{agent.title}</p>
                    </div>
                    <Badge className='border-2 cursor-pointer border-PrimaryBlue bg-white p-1 rounded-xl hover:text-white hover:bg-PrimaryBlue transition-all ease-in-out'>ViewAgent</Badge>
                </div>
            ))}
        </div>
    );
}
