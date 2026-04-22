import { asNumber, isRecord } from './runResult';

export type ReliabilityCardTone = 'default' | 'accent' | 'positive' | 'danger' | 'warning';

type ReliabilitySeverity = 'error' | 'warning' | 'info';

export type ReliabilityCategory = {
  issueCode: string;
  severity: ReliabilitySeverity;
  count: number;
};

export type ReliabilitySummaryView = {
  available: boolean;
  byCategory: ReliabilityCategory[];
  totalIssues: number | null;
  errorIssues: number | null;
  warningIssues: number | null;
  infoIssues: number | null;
  hasErrors: boolean;
  hasWarnings: boolean;
  statusLabel: string;
  statusTone: ReliabilityCardTone;
  gridColumnsClass: string;
};

function parseSeverity(value: unknown): ReliabilitySeverity {
  if (typeof value !== 'string') return 'info';
  const normalized = value.toLowerCase();
  if (normalized === 'error' || normalized === 'warning' || normalized === 'info') return normalized;
  return 'info';
}

function getGridColumnsClass(length: number) {
  if (length <= 1) return 'grid-cols-1';
  if (length === 2 || length === 4) return 'grid-cols-1 sm:grid-cols-2';
  return 'grid-cols-1 sm:grid-cols-3';
}

function coerceReliabilityCategories(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (!isRecord(item)) return null;
      const issueCode =
        typeof item.issueCode === 'string'
          ? item.issueCode
          : typeof item.issue_code === 'string'
            ? item.issue_code
            : '';
      if (!issueCode) return null;
      return {
        issueCode,
        severity: parseSeverity(item.severity),
        count: asNumber(item.count) ?? 0,
      };
    })
    .filter((item): item is ReliabilityCategory => item != null);
}

export function getReliabilitySummaryView(
  source: unknown,
  options?: { fallbackCountsToZero?: boolean },
): ReliabilitySummaryView {
  const fallbackCountsToZero = options?.fallbackCountsToZero ?? false;
  const summary = isRecord(source)
    ? isRecord(source.reliabilitySummary)
      ? source.reliabilitySummary
      : isRecord(source.reliability_summary)
        ? source.reliability_summary
        : source
    : null;

  if (!summary || !isRecord(summary)) {
    const emptyCount = fallbackCountsToZero ? 0 : null;
    return {
      available: false,
      byCategory: [],
      totalIssues: emptyCount,
      errorIssues: emptyCount,
      warningIssues: emptyCount,
      infoIssues: emptyCount,
      hasErrors: false,
      hasWarnings: false,
      statusLabel: 'Unavailable',
      statusTone: 'default',
      gridColumnsClass: 'grid-cols-1',
    };
  }

  const byCategory = coerceReliabilityCategories(summary.byCategory ?? summary.by_category);
  const inferredTotal = byCategory.reduce((sum, item) => sum + item.count, 0);
  const inferredErrors = byCategory
    .filter((item) => item.severity === 'error')
    .reduce((sum, item) => sum + item.count, 0);
  const inferredWarnings = byCategory
    .filter((item) => item.severity === 'warning')
    .reduce((sum, item) => sum + item.count, 0);
  const inferredInfo = byCategory
    .filter((item) => item.severity === 'info')
    .reduce((sum, item) => sum + item.count, 0);

  const totalIssues = asNumber(summary.totalIssues ?? summary.total_issues);
  const errorIssues = asNumber(summary.errorIssues ?? summary.error_issues);
  const warningIssues = asNumber(summary.warningIssues ?? summary.warning_issues);
  const infoIssues = asNumber(summary.infoIssues ?? summary.info_issues);
  const resolvedTotal = totalIssues ?? inferredTotal;
  const resolvedErrors = errorIssues ?? inferredErrors;
  const resolvedWarnings = warningIssues ?? inferredWarnings;
  const resolvedInfo = infoIssues ?? inferredInfo;
  const hasErrors = resolvedErrors > 0;
  const hasWarnings = resolvedWarnings > 0;

  return {
    available: true,
    byCategory,
    totalIssues: totalIssues ?? (fallbackCountsToZero ? resolvedTotal : totalIssues),
    errorIssues: errorIssues ?? (fallbackCountsToZero ? resolvedErrors : errorIssues),
    warningIssues: warningIssues ?? (fallbackCountsToZero ? resolvedWarnings : warningIssues),
    infoIssues: infoIssues ?? (fallbackCountsToZero ? resolvedInfo : infoIssues),
    hasErrors,
    hasWarnings,
    statusLabel: hasErrors
      ? 'Critical Issues Detected'
      : hasWarnings
        ? 'Minor Issues Detected'
        : 'No Issues Detected',
    statusTone: hasErrors ? 'danger' : hasWarnings ? 'warning' : 'positive',
    gridColumnsClass: getGridColumnsClass(byCategory.length),
  };
}
