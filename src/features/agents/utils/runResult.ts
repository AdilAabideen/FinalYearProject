// Provides run result helpers.
import { formatConfidence, formatInteger } from './format';

export type DecisionTone = 'positive' | 'danger' | 'neutral';

export type ResultViewModel = {
  decisionLabel: string;
  decisionTone: DecisionTone;
  confidenceLabel: string;
  caseSummary: string;
  justification: string;
  risks: string[];
  missingInformation: string[];
};

export type Esi345ResultViewModel = {
  esiLevelLabel: string;
  numResourcesLabel: string;
  predictedResources: string[];
};

export type AgentDecisionConfig = {
  decisionAliases: string[];
  trueLabel: string;
  falseLabel: string;
  trueKeywords: string[];
  falseKeywords: string[];
};

export const RESULT_ALIASES = {
  confidence: ['confidence', 'score', 'probability'],
  summary: ['case_summary', 'casesummary', 'summary'],
  risks: ['key_risks', 'keyrisks', 'risks'],
  missing: ['missing_information', 'missinginformation', 'missing_info', 'gaps'],
  justification: ['justification', 'rationale', 'reasoning'],
} as const;

export const ESI345_ALIASES = {
  esiLevel: ['esi_level', 'esilevel', 'esi', 'acuity', 'level'],
  numResources: ['num_resources', 'numresources', 'resource_count', 'resources_count'],
  predictedResources: [
    'predicted_resources',
    'predictedresources',
    'resources',
    'recommended_resources',
  ],
} as const;

const DEFAULT_DECISION_CONFIG: AgentDecisionConfig = {
  decisionAliases: ['decision', 'ok', 'final_decision', 'finaldecision'],
  trueLabel: 'Positive',
  falseLabel: 'Negative',
  trueKeywords: [],
  falseKeywords: [],
};

const ESI1_DECISION_CONFIG: AgentDecisionConfig = {
  decisionAliases: ['is_esi1', 'isesi1', 'ok', 'decision', 'final_decision', 'finaldecision'],
  trueLabel: 'ESI-1',
  falseLabel: 'Not ESI-1',
  trueKeywords: ['esi1', 'esi-1'],
  falseKeywords: ['esi2', 'esi-2', 'esi3', 'esi-3', 'esi4', 'esi-4', 'esi5', 'esi-5'],
};

const ESI2_DECISION_CONFIG: AgentDecisionConfig = {
  decisionAliases: ['is_esi2', 'isesi2', 'ok', 'decision', 'final_decision', 'finaldecision'],
  trueLabel: 'ESI-2',
  falseLabel: 'Not ESI-2',
  trueKeywords: ['esi2', 'esi-2'],
  falseKeywords: ['esi1', 'esi-1', 'esi3', 'esi-3', 'esi4', 'esi-4', 'esi5', 'esi-5'],
};

// Normalizes agent name.
function normalizeAgentName(name: string) {
  return name.trim().toLowerCase().replace(/[\s_-]+/g, '');
}

// Normalizes key.
export function normalizeKey(key: string) {
  return key.toLowerCase().replace(/[^a-z0-9]/g, '');
}

// Checks record.
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// Casts string.
export function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

// Casts number.
export function asNumber(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

// Handles to string array.
export function toStringArray(value: unknown) {
  if (Array.isArray(value)) {
// Handles filter.
// Maps logic.
    return value.map((item) => String(item)).filter((item) => item.trim().length > 0);
  }
  if (typeof value === 'string' && value.trim().length > 0) return [value];
  return [];
}

// Gets value by aliases.
export function getValueByAliases(record: Record<string, unknown>, aliases: readonly string[]) {
  const aliasSet = new Set(aliases.map(normalizeKey));
  for (const [key, value] of Object.entries(record)) {
    if (aliasSet.has(normalizeKey(key))) return value;
  }
  return undefined;
}

// Parses decision.
export function parseDecision(value: unknown) {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value > 0;
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (['true', 'yes', '1', 'retain', 'critical'].includes(normalized)) {
      return true;
    }
    if (['false', 'no', '0', 'defer'].includes(normalized)) {
      return false;
    }
  }
  return null;
}

// Parses decision with config.
export function parseDecisionWithConfig(value: unknown, config: AgentDecisionConfig) {
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (config.trueKeywords.includes(normalized)) return true;
    if (config.falseKeywords.includes(normalized)) return false;
  }
  return parseDecision(value);
}

// Checks esi1 config.
function isEsi1Config(config: AgentDecisionConfig) {
  return config.decisionAliases.map(normalizeKey).includes('isesi1');
}

// Checks esi2 config.
function isEsi2Config(config: AgentDecisionConfig) {
  return config.decisionAliases.map(normalizeKey).includes('isesi2');
}

// Gets agent decision config.
export function getAgentDecisionConfig(agentName: string): AgentDecisionConfig {
  const normalized = normalizeAgentName(agentName);
  if (normalized.includes('esi2')) return ESI2_DECISION_CONFIG;
  if (normalized.includes('esi1')) return ESI1_DECISION_CONFIG;
  return DEFAULT_DECISION_CONFIG;
}

// Checks esi345 agent name.
export function isEsi345AgentName(agentName: string) {
  const normalized = normalizeKey(agentName);
  return normalized.includes('esi345') || normalized.includes('es345');
}

// Handles resolve decision from record.
export function resolveDecisionFromRecord(record: Record<string, unknown>, config: AgentDecisionConfig) {
  const primaryRaw = getValueByAliases(record, config.decisionAliases);
  const primaryDecision = parseDecisionWithConfig(primaryRaw, config);
  if (primaryDecision != null || primaryRaw !== undefined) {
    return { raw: primaryRaw, decision: primaryDecision };
  }

  const inverseAliases = isEsi2Config(config)
    ? ['is_esi1', 'isesi1']
    : isEsi1Config(config)
      ? ['is_esi2', 'isesi2']
      : [];
  if (!inverseAliases.length) {
    return { raw: primaryRaw, decision: primaryDecision };
  }

  const inverseRaw = getValueByAliases(record, inverseAliases);
  const inverseDecision = parseDecision(inverseRaw);
  if (inverseDecision == null) {
    return { raw: inverseRaw, decision: null };
  }
  return { raw: inverseRaw, decision: !inverseDecision };
}

// Handles decision known aliases.
export function decisionKnownAliases(config: AgentDecisionConfig) {
  if (isEsi2Config(config)) return [...config.decisionAliases, 'is_esi1', 'isesi1'];
  if (isEsi1Config(config)) return [...config.decisionAliases, 'is_esi2', 'isesi2'];
  return config.decisionAliases;
}

// Formats decision display value.
export function formatDecisionDisplayValue(decision: boolean | null, raw: unknown) {
  if (decision != null) return decision ? 'True' : 'False';
  if (typeof raw === 'string') return raw;
  if (typeof raw === 'number') return String(raw);
  if (typeof raw === 'boolean') return raw ? 'True' : 'False';
  return '—';
}

// Handles decision tone to label.
function decisionToneToLabel(decision: boolean | null, raw: unknown, config: AgentDecisionConfig) {
  const decisionLabel =
    decision == null
      ? typeof raw === 'string'
        ? raw
        : 'Unknown'
      : decision
        ? config.trueLabel
        : config.falseLabel;
  const decisionTone: DecisionTone = decision == null ? 'neutral' : decision ? 'positive' : 'danger';
  return { decisionLabel, decisionTone };
}

// Builds result view model.
export function buildResultViewModel(
  output: Record<string, unknown>,
  config: AgentDecisionConfig,
  defaults?: { summaryFallback?: string; justificationFallback?: string },
): ResultViewModel {
  const { raw: decisionRaw, decision } = resolveDecisionFromRecord(output, config);
  const confidenceRaw = getValueByAliases(output, RESULT_ALIASES.confidence);
  const summaryRaw = getValueByAliases(output, RESULT_ALIASES.summary);
  const risksRaw = getValueByAliases(output, RESULT_ALIASES.risks);
  const missingRaw = getValueByAliases(output, RESULT_ALIASES.missing);
  const justificationRaw = getValueByAliases(output, RESULT_ALIASES.justification);
  const { decisionLabel, decisionTone } = decisionToneToLabel(decision, decisionRaw, config);

  return {
    decisionLabel,
    decisionTone,
    confidenceLabel: formatConfidence(asNumber(confidenceRaw)),
    caseSummary:
      typeof summaryRaw === 'string' && summaryRaw.trim().length > 0
        ? summaryRaw
        : (defaults?.summaryFallback ?? 'No summary was provided by the run output.'),
    justification:
      typeof justificationRaw === 'string' && justificationRaw.trim().length > 0
        ? justificationRaw
        : (defaults?.justificationFallback ?? 'No justification was provided by the run output.'),
    risks: toStringArray(risksRaw),
    missingInformation: toStringArray(missingRaw),
  };
}

// Builds esi345 result view model.
export function buildEsi345ResultViewModel(output: Record<string, unknown>): Esi345ResultViewModel {
  const esiLevelRaw = getValueByAliases(output, ESI345_ALIASES.esiLevel);
  const numResourcesRaw = getValueByAliases(output, ESI345_ALIASES.numResources);
  const predictedResourcesRaw = getValueByAliases(output, ESI345_ALIASES.predictedResources);
  const predictedResources = toStringArray(predictedResourcesRaw);
  const numResources = asNumber(numResourcesRaw);
  const esiLevel = asNumber(esiLevelRaw);

  return {
    esiLevelLabel:
      esiLevel == null
        ? typeof esiLevelRaw === 'string' && esiLevelRaw.trim().length > 0
          ? esiLevelRaw
          : '—'
        : formatInteger(esiLevel),
    numResourcesLabel:
      numResources == null
        ? predictedResources.length > 0
          ? formatInteger(predictedResources.length)
          : typeof numResourcesRaw === 'string' && numResourcesRaw.trim().length > 0
            ? numResourcesRaw
            : '—'
        : formatInteger(numResources),
    predictedResources,
  };
}

// Gets additional output entries.
export function getAdditionalOutputEntries(
  output: Record<string, unknown>,
  options: { decisionConfig: AgentDecisionConfig; includeEsi345Aliases?: boolean },
) {
  const resultAliases = options.includeEsi345Aliases
    ? [...ESI345_ALIASES.esiLevel, ...ESI345_ALIASES.numResources, ...ESI345_ALIASES.predictedResources]
    : decisionKnownAliases(options.decisionConfig);
  const knownKeys = new Set(
    [
      ...resultAliases,
      ...RESULT_ALIASES.confidence,
      ...RESULT_ALIASES.summary,
      ...RESULT_ALIASES.risks,
      ...RESULT_ALIASES.missing,
      ...RESULT_ALIASES.justification,
    ].map(normalizeKey),
  );
// Handles filter.
  return Object.entries(output).filter(([key]) => !knownKeys.has(normalizeKey(key)));
}
