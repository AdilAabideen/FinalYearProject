import type { PointerEvent } from 'react';
import { cn } from '../../../../shared/lib/cn';
import type { ToolCatalogItem } from '../../../../types/agents';
import { formatToolName } from '../../utils/diagram';

type ToolNodeProps = {
  tool: ToolCatalogItem;
  active: boolean;
  dragging: boolean;
  onActiveChange: (active: boolean) => void;
  onPointerDown: (e: PointerEvent<HTMLButtonElement>) => void;
  onPointerMove: (e: PointerEvent<HTMLButtonElement>) => void;
  onPointerUp: (e: PointerEvent<HTMLButtonElement>) => void;
  onPointerCancel: (e: PointerEvent<HTMLButtonElement>) => void;
  buttonRef: (node: HTMLButtonElement | null) => void;
};

// Renders the tool node.
export function ToolNode({
  tool,
  active,
  dragging,
  onActiveChange,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onPointerCancel,
  buttonRef,
}: ToolNodeProps) {
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
      <p className="truncate text-xs font-semibold text-slate-900">{formatToolName(tool.name)}</p>
      <p className="mt-1 max-h-9 overflow-hidden text-[11px] ml-0 leading-snug text-slate-600">
        {(() => {
          const sentences = tool.description.split(/[.!?]+/).filter((sentence) => sentence.trim());
          const firstOne = sentences.slice(0, 1).join('. ').trim();
          const words = firstOne.split(/\s+/);
          if (words.length > 15) {
            return `${words.slice(0, 15).join(' ')}...`;
          }
          return firstOne + (sentences.length > 1 ? '...' : '');
        })()}
      </p>
    </button>
  );
}
