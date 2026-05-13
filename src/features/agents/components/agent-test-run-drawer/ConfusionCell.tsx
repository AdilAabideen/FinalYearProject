import { formatInteger } from '../../utils/format';

// Renders the confusion cell.
export function ConfusionCell({
  label,
  value,
  tone,
  maxValue,
}: {
  label: string;
  value: number;
  tone: 'correct' | 'error';
  maxValue: number;
}) {
  const ratio = maxValue > 0 ? value / maxValue : 0;
  const strength = ratio > 0.66 ? 'strong' : ratio > 0.33 ? 'medium' : 'soft';
  const className =
    tone === 'correct'
      ? strength === 'strong'
        ? 'border-emerald-300 bg-emerald-100 text-emerald-900'
        : strength === 'medium'
          ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
          : 'border-emerald-100 bg-emerald-50/40 text-emerald-900'
      : strength === 'strong'
        ? 'border-rose-300 bg-rose-100 text-rose-900'
        : strength === 'medium'
          ? 'border-rose-200 bg-rose-50 text-rose-900'
          : 'border-rose-100 bg-rose-50/40 text-rose-900';

  return (
    <div className={`rounded-xl border p-3 ${className}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-xl font-semibold">{formatInteger(value)}</p>
    </div>
  );
}
