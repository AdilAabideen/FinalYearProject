export function titleCaseKey(key: string) {
  return key
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function formatInteger(value: number | null) {
  if (value == null) return '—';
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}

export function formatDuration(seconds: number | null) {
  if (seconds == null) return '—';
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  return `${seconds.toFixed(seconds < 10 ? 2 : 1)} s`;
}

export function formatLatencyMs(value: number | null) {
  if (value == null) return '—';
  if (value < 10) return `${value.toFixed(2)} ms`;
  if (value < 100) return `${value.toFixed(1)} ms`;
  return `${Math.round(value)} ms`;
}

export function formatCurrency(value: number | null) {
  if (value == null) return '—';
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 4,
  }).format(value);
}

export function formatConfidence(value: number | null) {
  if (value == null) return '—';
  const ratio = value > 1 ? value / 100 : value;
  return `${Math.round(Math.max(0, Math.min(1, ratio)) * 100)}%`;
}

export function formatPercent(value: number | null, digits = 1) {
  if (value == null || !Number.isFinite(value)) return '—';
  const ratio = value > 1 ? value / 100 : value;
  const clamped = Math.max(0, Math.min(1, ratio));
  return `${(clamped * 100).toFixed(digits)}%`;
}
