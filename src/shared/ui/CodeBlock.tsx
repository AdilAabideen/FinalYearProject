import { cn } from '../lib/cn';

type CodeBlockProps = {
  code: string;
  className?: string;
};

export function CodeBlock({ code, className }: CodeBlockProps) {
  return (
    <pre
      className={cn(
        'overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs leading-relaxed text-slate-800',
        className,
      )}
    >
      <code>{code}</code>
    </pre>
  );
}

