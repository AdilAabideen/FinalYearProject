import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { cn } from '../../../shared/lib/cn';
import { Badge } from '../../../shared/ui/Badge';
import type { AgentCatalogDetail } from '../../../types/agents';
import { ToolNode } from './agent-diagram/ToolNode';
import { ToolSchemaPopover } from './agent-diagram/ToolSchemaPopover';
import {
  clamp,
  curvedConnectorPath,
  getSchemaLabel,
  makeInitialPositions,
  type DiagramPoint as Point,
} from '../utils/diagram';

type AgentDiagramProps = {
  agent: AgentCatalogDetail;
};

type DragState = {
  index: number;
  pointerId: number;
  offsetX: number;
  offsetY: number;
  halfWidth: number;
  halfHeight: number;
};

// Renders the agent diagram.
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

// Cancels close.
  function cancelClose() {
    if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current);
    closeTimerRef.current = null;
  }

// Schedules close.
  function scheduleClose(delay = 120) {
    cancelClose();
    closeTimerRef.current = window.setTimeout(() => {
      if (popoverHoverRef.current) return;
      setActiveToolIndex(null);
    }, delay);
  }

// Updates tool position.
  function updateToolPosition(index: number, next: Point) {
    setToolPositions((prev) => {
      if (prev[index]?.x === next.x && prev[index]?.y === next.y) return prev;
      const copy = prev.slice();
      copy[index] = next;
      return copy;
    });
  }

// Handles pointer down.
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

// Handles pointer move.
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

// Handles pointer end.
  function handlePointerEnd(e: React.PointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    dragRef.current = null;
    setDraggingIndex(null);
    scheduleClose(250);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
    }
  }

  useLayoutEffect(() => {
    return () => cancelClose();
  }, []);

  useLayoutEffect(() => {
    let frame: number | null = null;

// Schedules logic.
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
