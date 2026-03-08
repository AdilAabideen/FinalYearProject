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

function formatLabel(label: string) {
  if (!label) return label;
  if (label.startsWith('[')) return label;
  return label.charAt(0).toUpperCase() + label.slice(1);
}

type RenderOptions = {
  depth: number;
  maxDepth: number;
  path: string;
  ancestors: ReadonlyArray<object>;
};

function PrimitiveRow({ label, value }: { label: string; value: string }) {
  const formattedLabel = formatLabel(label);
  return (
    <p className="whitespace-pre-wrap break-words leading-snug">
      <span className="font-semibold text-slate-700">{formattedLabel}</span>{' '}
      <span className="text-slate-500">{value}</span>
    </p>
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

  const containerRef = value as object;
  if (opts.ancestors.includes(containerRef)) {
    return <PrimitiveRow label={label} value="[Circular]" />;
  }

  const children = renderValue(value, {
    ...opts,
    depth: opts.depth + 1,
    path: opts.path,
    ancestors: [...opts.ancestors, containerRef],
  });

  return (
    <div className="space-y-1">
      <p className="break-words font-semibold leading-snug text-slate-700">{formatLabel(label)}</p>
      <div className={cn('border-l border-slate-200', indentClass(opts.depth + 1))}>
        <div className="mt-1 space-y-1">{children}</div>
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

  const ancestors = isContainer(value) ? [value as object] : [];
  return (
    <div className={cn('space-y-1 text-xs', className)}>
      {renderValue(value, { depth: 0, maxDepth, path: '', ancestors })}
    </div>
  );
}
