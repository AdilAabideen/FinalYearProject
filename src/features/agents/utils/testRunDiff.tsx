import { Badge } from '../../../shared/ui/Badge';
import { JsonInspector } from '../../../shared/ui/JsonInspector';
import { AgentStatCard } from '../components/shared/AgentStatCard';
import { formatConfidence, formatInteger } from './format';
import {
  asNumber,
  formatDecisionDisplayValue,
  getAgentDecisionConfig,
  isRecord,
  parseDecision,
  resolveDecisionFromRecord,
  toStringArray,
  type AgentDecisionConfig,
} from './runResult';

// Handles prefixed record.
function prefixedRecord(record: Record<string, unknown>, prefix: string) {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(record)) {
    if (!key.startsWith(prefix)) continue;
    out[key.slice(prefix.length)] = value;
  }
  return out;
}

// Renders generic diff.
function renderGenericDiff(diff: Record<string, unknown>) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-sm font-semibold text-slate-900">Diff</p>
      <p className="mt-1 text-xs text-slate-600">No agent-specific renderer configured for this agent.</p>
      <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
        <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-slate-600">
          Raw Diff JSON
        </summary>
        <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-white p-3">
          <JsonInspector value={diff} />
        </div>
      </details>
    </div>
  );
}

// Renders decision diff.
function renderDecisionDiff(diff: Record<string, unknown>, config: AgentDecisionConfig) {
  const expectedAnswer = isRecord(diff.expected_answer) ? diff.expected_answer : {};
  const agentAnswer = isRecord(diff.agent_answer) ? diff.agent_answer : {};
  const expectedRootRecord = prefixedRecord(diff, 'expected_');
  const actualRootRecord = prefixedRecord(diff, 'actual_');
  const expectedDecisionSource = { ...expectedRootRecord, ...expectedAnswer };

  const expectedAcuity = asNumber(expectedAnswer.acuity);
  const { raw: agentDecisionRaw, decision: agentDecision } = resolveDecisionFromRecord(agentAnswer, config);
  const { decision: expectedDecision } = resolveDecisionFromRecord(expectedDecisionSource, config);
  const { decision: actualDecision } = resolveDecisionFromRecord(actualRootRecord, config);
  const confidence = asNumber(agentAnswer.confidence);

  const passed = typeof diff.passed === 'boolean' ? diff.passed : null;
  const inferredMatch =
    expectedDecision != null && actualDecision != null
      ? expectedDecision === actualDecision
      : expectedDecision != null && agentDecision != null
        ? expectedDecision === agentDecision
        : null;
  const isMatch = passed ?? inferredMatch;

  const verdictLabel = isMatch == null ? 'Not enough data' : isMatch ? 'Success' : 'Mismatch';
  const verdictBadgeClass =
    isMatch == null
      ? 'bg-slate-100 text-slate-700 ring-slate-200'
      : isMatch
        ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
        : 'bg-rose-50 text-rose-700 ring-rose-200';
  const panelClass =
    isMatch == null
      ? 'border-slate-200 bg-white'
      : isMatch
        ? 'border-emerald-200 bg-emerald-50/40'
        : 'border-rose-200 bg-rose-50/40';

  return (
    <div className="space-y-4 pb-2">
      <section className={`rounded-2xl border p-4 ${panelClass}`}>
        <div className="flex items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-slate-900">Diff</h4>
          <Badge className={verdictBadgeClass}>{verdictLabel}</Badge>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <AgentStatCard
            label={`Agent Response (${config.trueLabel})`}
            value={formatDecisionDisplayValue(agentDecision, agentDecisionRaw)}
            tone={isMatch == null ? 'default' : isMatch ? 'positive' : 'danger'}
          />
          <AgentStatCard label="Confidence" value={formatConfidence(confidence)} tone="accent" />
          <AgentStatCard
            label="Expected Acuity"
            value={expectedAcuity == null ? '—' : formatInteger(expectedAcuity)}
            tone={isMatch == null ? 'default' : isMatch ? 'positive' : 'danger'}
          />
        </div>
      </section>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
          Raw Diff JSON
        </summary>
        <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <JsonInspector value={diff} />
        </div>
      </details>
    </div>
  );
}

// Renders esi345 decision diff.
function renderESI345DecisionDiff(diff: Record<string, unknown>, config: AgentDecisionConfig) {
  const expectedAnswer = isRecord(diff.expected_answer) ? diff.expected_answer : {};
  const agentAnswer = isRecord(diff.agent_answer) ? diff.agent_answer : {};
  const expectedAcuity = asNumber(diff.expected_acuity ?? expectedAnswer.acuity);
  const expectedResourcesUsed = asNumber(diff.expected_resources_used ?? expectedAnswer.resources_used);
  const actualAcuity = asNumber(diff.actual_acuity ?? agentAnswer.esi_level);
  const actualResourcesUsed = asNumber(diff.actual_resources_used ?? agentAnswer.num_resources);
  const confidence = asNumber(agentAnswer.confidence);
  const predictedResources = toStringArray(agentAnswer.predicted_resources);
  const caseSummary =
    typeof agentAnswer.case_summary === 'string' && agentAnswer.case_summary.trim().length > 0
      ? agentAnswer.case_summary
      : 'No case summary was provided in the diff payload.';

  const passedFromFlag = typeof diff.passed === 'boolean' ? diff.passed : null;
  const verdictRaw = typeof diff.verdict === 'string' ? diff.verdict.trim().toLowerCase() : '';
  const passedFromVerdict = verdictRaw === 'pass' ? true : verdictRaw === 'fail' ? false : null;
  const passed = passedFromFlag ?? passedFromVerdict;
  const warning = parseDecision(diff.warning);
  const acuityMatch = parseDecision(diff.acuity_match);
  const resourcesMatch = parseDecision(diff.resources_match);
  const hasWarning = warning === true;
  const isPass = passed === true;
  const isFail = passed === false;
  const isWarn = isPass && hasWarning;

  const verdictLabel = isPass ? (isWarn ? 'Pass With Warning' : 'Pass') : isFail ? 'Fail' : 'Unknown';
  const verdictBadgeClass = isWarn
    ? 'bg-amber-50 text-amber-700 ring-amber-200'
    : isPass
      ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
      : isFail
        ? 'bg-rose-50 text-rose-700 ring-rose-200'
        : 'bg-slate-100 text-slate-700 ring-slate-200';
  const panelClass = isWarn
    ? 'border-amber-200 bg-amber-50/40'
    : isPass
      ? 'border-emerald-200 bg-emerald-50/40'
      : isFail
        ? 'border-rose-200 bg-rose-50/40'
        : 'border-slate-200 bg-white';
  const tone = isWarn ? 'accent' : isPass ? 'positive' : isFail ? 'danger' : 'default';

  return (
    <div className="space-y-4 pb-2">
      <section className={`rounded-2xl border p-4 ${panelClass}`}>
        <div className="flex items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-slate-900">Diff</h4>
          <Badge className={verdictBadgeClass}>{verdictLabel}</Badge>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <AgentStatCard label="Actual Acuity" value={formatInteger(actualAcuity)} tone={tone} />
          <AgentStatCard
            label="Actual Resources Used"
            value={formatInteger(actualResourcesUsed)}
            tone={tone}
          />
          <AgentStatCard label="Confidence" value={formatConfidence(confidence)} tone="accent" />
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-4">
          <AgentStatCard label="Expected Acuity" value={formatInteger(expectedAcuity)} />
          <AgentStatCard label="Expected Resources" value={formatInteger(expectedResourcesUsed)} />
          <AgentStatCard
            label={`Acuity Match (${config.trueLabel})`}
            value={acuityMatch == null ? '—' : acuityMatch ? 'True' : 'False'}
            tone={acuityMatch == null ? 'default' : acuityMatch ? 'positive' : 'danger'}
          />
          <AgentStatCard
            label="Resources Match"
            value={resourcesMatch == null ? '—' : resourcesMatch ? 'True' : 'False'}
            tone={resourcesMatch == null ? 'default' : resourcesMatch ? 'positive' : 'danger'}
          />
        </div>

        <div className="mt-3 rounded-2xl border border-slate-200 bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Predicted Resources</p>
          {predictedResources.length ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {predictedResources.map((resource, index) => (
                <Badge key={`predicted-resource-${index}`} className="bg-sky-50 text-sky-700 ring-sky-200">
                  {resource}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-500">No predicted resources were returned.</p>
          )}
        </div>

        <div className="mt-3 rounded-2xl border border-slate-200 bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Case Summary</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-800">{caseSummary}</p>
        </div>
      </section>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer select-none text-sm font-semibold text-slate-800">
          Raw Diff JSON
        </summary>
        <div className="mt-3 max-h-[min(24rem,50vh)] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <JsonInspector value={diff} />
        </div>
      </details>
    </div>
  );
}

// Handles resolve diff renderer.
export function resolveDiffRenderer(agentName: string) {
  const config = getAgentDecisionConfig(agentName);
  return (diff: Record<string, unknown>) => {
    const normalized = agentName.trim().toLowerCase().replace(/[\s_-]+/g, '');
    if (normalized === 'esi345agent' || normalized.includes('esi345') || normalized.includes('es345')) {
      return renderESI345DecisionDiff(diff, config);
    }
    if (normalized.includes('esi')) {
      return renderDecisionDiff(diff, config);
    }
    return renderGenericDiff(diff);
  };
}
