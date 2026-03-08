import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';

type JsonInspectorProps = {
  value: unknown;
  className?: string;
  maxDepth?: number;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function formatPrimitive(value: unknown) {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
    return String(value);
  }
  return String(value);
}

function summarizeContainer(value: Record<string, unknown> | unknown[]) {
  if (Array.isArray(value)) return `Array (${value.length})`;
  return `Object (${Object.keys(value).length})`;
}

function indentClass(depth: number) {
  if (depth <= 0) return '';
  if (depth === 1) return 'pl-3';
  return 'pl-6';
}

function isContainer(value: unknown): value is Record<string, unknown> | unknown[] {
  return isPlainObject(value) || Array.isArray(value);
}

type RenderOptions = {
  depth: number;
  maxDepth: number;
  path: string;
  seen: WeakSet<object>;
};

function PrimitiveRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span className="shrink-0 font-semibold text-slate-700">{label}</span>
      <span className="min-w-0 flex-1 whitespace-pre-wrap break-words text-slate-500">{value}</span>
    </div>
  );
}

function ContainerBlock({
  label,
  value,
  opts,
}: {
  label: string;
  value: Record<string, unknown> | unknown[];
  opts: RenderOptions;
}) {
  if (opts.depth >= opts.maxDepth) {
    return <PrimitiveRow label={label} value={summarizeContainer(value)} />;
  }

  if (opts.seen.has(value as object)) {
    return <PrimitiveRow label={label} value="[Circular]" />;
  }
  opts.seen.add(value as object);

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="shrink-0 font-semibold text-slate-700">{label}</span>
      </div>
      <div className={cn('border-l border-slate-200', indentClass(opts.depth + 1))}>
        <div className="mt-1 space-y-2">
          {renderValue(value, {
            ...opts,
            depth: opts.depth + 1,
            path: opts.path,
          })}
        </div>
      </div>
    </div>
  );
}

function renderValue(value: unknown, opts: RenderOptions): ReactNode {
  if (Array.isArray(value)) {
    if (!value.length) {
      return <p className="text-slate-400">Empty array.</p>;
    }
    return value.map((item, index) => {
      const label = `[${index}]`;
      const path = opts.path ? `${opts.path}[${index}]` : `[${index}]`;
      if (isContainer(item)) {
        return (
          <ContainerBlock
            key={path}
            label={label}
            value={item}
            opts={{ ...opts, path }}
          />
        );
      }
      return <PrimitiveRow key={path} label={label} value={formatPrimitive(item)} />;
    });
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value);
    if (!entries.length) {
      return <p className="text-slate-400">Empty object.</p>;
    }
    return entries.map(([key, childValue]) => {
      const path = opts.path ? `${opts.path}.${key}` : key;
      if (isContainer(childValue)) {
        return (
          <ContainerBlock
            key={path}
            label={key}
            value={childValue}
            opts={{ ...opts, path }}
          />
        );
      }
      return <PrimitiveRow key={path} label={key} value={formatPrimitive(childValue)} />;
    });
  }

  return <PrimitiveRow label="Value" value={formatPrimitive(value)} />;
}

export function JsonInspector({ value, className, maxDepth = 6 }: JsonInspectorProps) {
  return (
    <div className={cn('space-y-2 text-xs leading-relaxed', className)}>
      {renderValue(value, { depth: 0, maxDepth, path: '', seen: new WeakSet<object>() })}
    </div>
  );
}
