// Provides status helpers.
export type ToolStatus = 'succeeded' | 'error' | 'unknown';

// Handles run status badge class.
export function runStatusBadgeClass(status: string) {
  const normalized = status.toLowerCase();
  if (
    normalized.includes('success') ||
    normalized.includes('succeed') ||
    normalized.includes('complete')
  ) {
    return 'bg-emerald-50 text-emerald-700 ring-emerald-200';
  }
  if (normalized.includes('fail') || normalized.includes('error')) {
    return 'bg-rose-50 text-rose-700 ring-rose-200';
  }
  if (normalized.includes('run')) {
    return 'bg-amber-50 text-amber-700 ring-amber-200';
  }
  return 'bg-slate-100 text-slate-700 ring-slate-200';
}

// Formats status label.
export function formatStatusLabel(status: string) {
  if (!status.length) return status;
  return status.charAt(0).toUpperCase() + status.slice(1);
}

// Handles classify tool status.
export function classifyToolStatus(status: string | null | undefined): ToolStatus {
  if (!status) return 'unknown';
  const normalized = status.toLowerCase();
  if (
    normalized.includes('succeed') ||
    normalized.includes('success') ||
    normalized.includes('complete') ||
    normalized.includes('done')
  ) {
    return 'succeeded';
  }
  if (normalized.includes('error') || normalized.includes('fail')) return 'error';
  return 'unknown';
}

// Handles tool status badge class.
export function toolStatusBadgeClass(status: ToolStatus) {
  if (status === 'succeeded') return 'bg-emerald-50 text-emerald-700 ring-emerald-200';
  if (status === 'error') return 'bg-rose-50 text-rose-700 ring-rose-200';
  return 'bg-slate-100 text-slate-700 ring-slate-200';
}
