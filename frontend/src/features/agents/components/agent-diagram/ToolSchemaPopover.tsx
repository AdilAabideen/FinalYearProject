import { cn } from '../../../../shared/lib/cn';
import { formatJson } from '../../../../shared/lib/formatJson';
import { Badge } from '../../../../shared/ui/Badge';
import { CodeBlock } from '../../../../shared/ui/CodeBlock';
import type { ToolCatalogItem } from '../../../../types/agents';
import { formatToolName } from '../../utils/diagram';

type ToolSchemaPopoverProps = {
  tool: ToolCatalogItem;
  style: { left: number; top: number; maxHeight: number; arrowOffset: number };
  visible: boolean;
  popoverRef: (node: HTMLDivElement | null) => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
};

// Renders the tool schema popover.
export function ToolSchemaPopover({
  tool,
  style,
  visible,
  popoverRef,
  onMouseEnter,
  onMouseLeave,
}: ToolSchemaPopoverProps) {
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
          <p className="truncate text-sm font-semibold text-slate-900">{formatToolName(tool.name)}</p>
          {tool.description ? (
            <p className="mt-0.5 text-xs text-slate-600">
              {(() => {
                const sentences = tool.description.split(/[.!?]+/).filter((sentence) => sentence.trim());
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
