import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { cn } from '../../lib/cn';
import { formatJson } from '../../lib/formatJson';
import type { AgentCatalogDetail, ToolCatalogItem } from '../../types/agents';
import { Badge } from '../ui/Badge';
import { CodeBlock } from '../ui/CodeBlock';

type AgentDiagramProps = {
  agent: AgentCatalogDetail;
};

type Point = { x: number; y: number };
type DragState = {
  index: number;
  pointerId: number;
  offsetX: number;
  offsetY: number;
  halfWidth: number;
  halfHeight: number;
};

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

function makeInitialPositions(count: number) {
  return computeRadialPositions(count).map((p) => {
    const dx = p.x - 50;
    const dy = p.y - 50;
    const x = 50 + dx * 0.82;
    const y = 50 + dy * 0.9;

    return {
      x: clamp(x, 14, 86),
      y: clamp(y, 12, 88),
    };
  });
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
  dragging,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onPointerCancel,
  buttonRef,
}: {
  tool: ToolCatalogItem;
  active: boolean;
  onActiveChange: (active: boolean) => void;
  dragging: boolean;
  onPointerDown: (e: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerMove: (e: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerUp: (e: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerCancel: (e: React.PointerEvent<HTMLButtonElement>) => void;
  buttonRef: (node: HTMLButtonElement | null) => void;
}) {
  return (
    <button
      type="button"
      ref={buttonRef}
      className={cn(
        'group relative z-10 w-52 select-none touch-none rounded-xl border border-PrimaryBlue bg-white px-3 py-2 text-center shadow-sm transition-all focus:outline-none focus:ring-4 focus:ring-PrimaryBlue/20 sm:w-56 hover:border-2',
        active && 'border-2',
        dragging ? 'cursor-grabbing' : 'cursor-grab',
      )}
      onMouseEnter={() => onActiveChange(true)}
      onMouseLeave={() => onActiveChange(false)}
      onFocus={() => onActiveChange(true)}
      onBlur={() => onActiveChange(false)}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
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
    </button>
  );
}

function ToolSchemaPopover({
  tool,
  style,
  popoverRef,
  visible,
  onMouseEnter,
  onMouseLeave,
}: {
  tool: ToolCatalogItem;
  style: { left: number; top: number; maxHeight: number; arrowOffset: number };
  popoverRef: (node: HTMLDivElement | null) => void;
  visible: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}) {
  return (
    <div
      ref={popoverRef}
      className={cn(
        'absolute z-30 flex w-[26rem] -translate-x-1/2 -translate-y-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-xl transition-opacity',
        visible ? 'opacity-100' : 'pointer-events-none opacity-0',
      )}
      style={{
        left: style.left,
        top: style.top,
        maxHeight: style.maxHeight,
        height: style.maxHeight,
      }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      role="dialog"
      aria-label={`${tool.name} schema`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">
            {ConvertToolName(tool.name)}
          </p>
          {tool.description ? (
            <p className="mt-0.5 text-xs text-slate-600">
              {(() => {
                const sentences = tool.description.split(/[.!?]+/).filter((s) => s.trim());
                const firstTwo = sentences.slice(0, 2).join('. ').trim();
                const words = firstTwo.split(/\s+/);
                if (words.length > 28) return `${words.slice(0, 28).join(' ')}...`;
                return firstTwo + (sentences.length > 2 ? '...' : '');
              })()}
            </p>
          ) : null}
        </div>
        <Badge className="shrink-0 bg-PrimaryBlue/10 text-PrimaryBlue ring-PrimaryBlue/20">
          Schema
        </Badge>
      </div>

      <div className="mt-3 min-h-0 flex-1 overflow-hidden">
        <CodeBlock
          code={formatJson(tool.argsSchema)}
          className="min-h-0 h-full overflow-auto border-0 bg-slate-50 p-2 text-left"
        />
      </div>

      <div
        aria-hidden="true"
        className="absolute top-full h-3 w-3 -translate-x-1/2 -translate-y-1/2 rotate-45 border border-slate-200 bg-white"
        style={{ left: `calc(50% + ${style.arrowOffset}px)` }}
      />
    </div>
  );
}

export function AgentDiagram({ agent }: AgentDiagramProps) {
  const [activeToolIndex, setActiveToolIndex] = useState<number | null>(null);
  const [toolPositions, setToolPositions] = useState<Point[]>(() =>
    makeInitialPositions(agent.tools.length),
  );
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const closeTimerRef = useRef<number | null>(null);
  const popoverHoverRef = useRef(false);
  const toolButtonRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const [popoverStyle, setPopoverStyle] = useState<{
    left: number;
    top: number;
    maxHeight: number;
    arrowOffset: number;
  } | null>(null);

  const positions = toolPositions;
  const inputLabel = useMemo(() => getSchemaLabel(agent.inputSchema), [agent.inputSchema]);
  const tooltipsDisabled = draggingIndex !== null;
  const popoverIndex = tooltipsDisabled ? null : activeToolIndex;

  function cancelClose() {
    if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current);
    closeTimerRef.current = null;
  }

  function scheduleClose(delay = 120) {
    cancelClose();
    closeTimerRef.current = window.setTimeout(() => {
      if (popoverHoverRef.current) return;
      setActiveToolIndex(null);
    }, delay);
  }

  function updateToolPosition(index: number, next: Point) {
    setToolPositions((prev) => {
      if (prev[index]?.x === next.x && prev[index]?.y === next.y) return prev;
      const copy = prev.slice();
      copy[index] = next;
      return copy;
    });
  }

  function handlePointerDown(index: number) {
    return (e: React.PointerEvent<HTMLButtonElement>) => {
      if (e.button !== 0) return;
      const container = containerRef.current;
      if (!container) return;

      const nodeRect = e.currentTarget.getBoundingClientRect();
      const nodeCenterX = nodeRect.left + nodeRect.width / 2;
      const nodeCenterY = nodeRect.top + nodeRect.height / 2;

      dragRef.current = {
        index,
        pointerId: e.pointerId,
        offsetX: e.clientX - nodeCenterX,
        offsetY: e.clientY - nodeCenterY,
        halfWidth: nodeRect.width / 2,
        halfHeight: nodeRect.height / 2,
      };

      cancelClose();
      setDraggingIndex(index);
      setActiveToolIndex(index);
      e.currentTarget.setPointerCapture(e.pointerId);
      e.preventDefault();
    };
  }

  function handlePointerMove(e: React.PointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const desiredCenterX = e.clientX - drag.offsetX;
    const desiredCenterY = e.clientY - drag.offsetY;

    const clampedCenterX = clamp(
      desiredCenterX,
      rect.left + drag.halfWidth,
      rect.right - drag.halfWidth,
    );
    const clampedCenterY = clamp(
      desiredCenterY,
      rect.top + drag.halfHeight,
      rect.bottom - drag.halfHeight,
    );

    const x = ((clampedCenterX - rect.left) / rect.width) * 100;
    const y = ((clampedCenterY - rect.top) / rect.height) * 100;

    updateToolPosition(drag.index, { x: clamp(x, 0, 100), y: clamp(y, 0, 100) });
  }

  function handlePointerEnd(e: React.PointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    dragRef.current = null;
    setDraggingIndex(null);
    scheduleClose(250);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  }

  useLayoutEffect(() => {
    return () => cancelClose();
  }, []);

  useLayoutEffect(() => {
    let frame: number | null = null;

    const schedule = (fn: () => void) => {
      if (frame) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(fn);
    };

    if (popoverIndex === null) {
      schedule(() => setPopoverStyle(null));
      return () => {
        if (frame) cancelAnimationFrame(frame);
      };
    }

    const container = containerRef.current;
    const anchor = toolButtonRefs.current[popoverIndex];
    if (!container || !anchor) return;

    const containerRect = container.getBoundingClientRect();
    const anchorRect = anchor.getBoundingClientRect();
    const popRect = popoverRef.current?.getBoundingClientRect();
    const assumedWidth = 26 * 16;
    const popWidth = popRect?.width ?? assumedWidth;

    const margin = 12;
    const gap = 12;

    const anchorCenterX = anchorRect.left - containerRect.left + anchorRect.width / 2;
    const anchorTop = anchorRect.top - containerRect.top;

    const minX = margin + popWidth / 2;
    const maxX = containerRect.width - margin - popWidth / 2;
    const left = minX > maxX ? containerRect.width / 2 : clamp(anchorCenterX, minX, maxX);

    const availableHeight = anchorTop - gap - margin;
    const maxHeight = availableHeight > 160 ? Math.min(560, availableHeight) : 160;

    const half = popWidth / 2;
    const arrowOffset = clamp(anchorCenterX - left, -half + 18, half - 18);
    const next = { left, top: anchorTop - gap, maxHeight, arrowOffset };

    schedule(() => {
      setPopoverStyle((prev) =>
        prev &&
        Math.abs(prev.left - next.left) < 0.5 &&
        Math.abs(prev.top - next.top) < 0.5 &&
        Math.abs(prev.maxHeight - next.maxHeight) < 0.5 &&
        Math.abs(prev.arrowOffset - next.arrowOffset) < 0.5
          ? prev
          : next,
      );
    });

    return () => {
      if (frame) cancelAnimationFrame(frame);
    };
  }, [popoverIndex, toolPositions]);

  return (
    <div ref={containerRef} className="relative h-full w-full">
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
          if (!p) return null;
          const dist = Math.hypot(p.x - 50, p.y - 50) || 1;
          const curve = (i % 2 === 0 ? 1 : -1) * clamp(18 - dist / 2.5, 8, 22);
          const d = curvedConnectorPath({ x: 50, y: 50 }, p, curve);

          return (
            <path
              key={`${p.x}-${p.y}`}
              d={d}
              fill="none"
              strokeLinecap="round"
              className={cn(
                'transition-colors',
                activeToolIndex === i ? 'stroke-PrimaryBlue' : 'stroke-slate-300',
              )}
              strokeWidth={activeToolIndex === i ? 1.0 : 0.6}
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
              onActiveChange={(isActive) => {
                if (isActive) {
                  cancelClose();
                  setActiveToolIndex(i);
                } else {
                  scheduleClose();
                }
              }}
              dragging={draggingIndex === i}
              onPointerDown={handlePointerDown(i)}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerEnd}
              onPointerCancel={handlePointerEnd}
              buttonRef={(node) => {
                toolButtonRefs.current[i] = node;
              }}
            />
          </div>
        );
      })}

      {popoverIndex !== null ? (
        <ToolSchemaPopover
          tool={agent.tools[popoverIndex]}
          style={popoverStyle ?? { left: 0, top: 0, maxHeight: 160, arrowOffset: 0 }}
          popoverRef={(node) => {
            popoverRef.current = node;
          }}
          visible={popoverStyle !== null}
          onMouseEnter={() => {
            popoverHoverRef.current = true;
            cancelClose();
          }}
          onMouseLeave={() => {
            popoverHoverRef.current = false;
            scheduleClose(120);
          }}
        />
      ) : null}
    </div>
  );
}
