import { Badge } from '../../../../shared/ui/Badge';
import type { ToolStatus } from '../../utils/status';
import { TraceOutputHoverBadge } from '../TraceOutputHoverBadge';
import { ToolStatusBadge } from '../ToolStatusBadge';
import { prettifyToolName, truncateText } from '../../utils/trace';

export type TraceEntry =
  | {
    id: string;
    kind: 'thinking';
    output: {
      step: string;
      thought: string;
    } | null;
  }
  | {
    id: string;
    kind: 'action';
    toolName: string;
    status: ToolStatus;
    output: unknown;
  };

// Checks record.
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// Renders the agent trace plan entry.
function AgentTracePlanEntry({ entry }: { entry: Extract<TraceEntry, { kind: 'action' }> }) {
  const parsedOutput = isRecord(entry.output) ? entry.output : {};
  const parsedResult = isRecord(parsedOutput.result) ? parsedOutput.result : {};
  const notes = typeof parsedResult.notes === 'string' ? parsedResult.notes : '';
  const objective =
    typeof parsedResult.objective === 'string'
      ? parsedResult.objective
      : typeof parsedResult.objectives === 'string'
        ? parsedResult.objectives
        : '';
  const steps = Array.isArray(parsedResult.steps)
    ? parsedResult.steps.filter(
        (step): step is { step_id: string; description: string } =>
          typeof step === 'object' &&
          step !== null &&
          'step_id' in step &&
          'description' in step &&
          typeof step.description === 'string',
      )
    : [];

  return (
    <div key={entry.id} className="space-y-1">
      <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">PLAN</p>
      <div className="flex flex-wrap items-center flex-row">
        <p className="text-sm text-slate-800 font-semibold">Notes :&nbsp;</p>
        <p className="text-sm text-slate-800">{truncateText(notes, 2000)}</p>
      </div>
      <div className="flex flex-wrap items-center flex-row">
        <p className="text-sm text-slate-800 font-semibold">Objective :&nbsp;</p>
        <p className="text-sm text-slate-800">{truncateText(objective, 2000)}</p>
      </div>
      <p className="text-sm font-semibold text-slate-900">Steps :</p>
      {steps.length ? (
        <ul className="list-disc space-y-1 pl-6 text-sm text-slate-800">
          {steps.map((step, index) => (
            <li key={`${entry.id}-step-${index}`}>
              {truncateText(step.step_id, 2000)}: {truncateText(step.description, 2000)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">No steps provided.</p>
      )}
    </div>
  );
}

// Renders the agent trace thought entry.
function AgentTraceThoughtEntry({ entry }: { entry: Extract<TraceEntry, { kind: 'thinking' }> }) {
  const thoughtStep = entry.output?.step ?? 'Thought';
  const thoughtText = entry.output?.thought ?? 'No thought content.';

  return (
    <div key={entry.id} className="space-y-1">
      <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">THINKING</p>
      <p>
        <span className="text-sm text-slate-900 font-bold">{truncateText(thoughtStep, 2000)}</span>:{' '}
        <span className="text-sm text-slate-800">{truncateText(thoughtText, 2000)}</span>
      </p>
    </div>
  );
}

// Renders the agent trace resource entry.
function AgentTraceResourceEntry({ entry }: { entry: Extract<TraceEntry, { kind: 'action' }> }) {
  const payloadRecord = isRecord(entry.output) ? entry.output : null;
  const outputRecord = payloadRecord && isRecord(payloadRecord.result) ? payloadRecord.result : payloadRecord;
  const resourceName =
    outputRecord && typeof outputRecord.resource_name === 'string' ? outputRecord.resource_name : 'None';
  const justification =
    outputRecord && typeof outputRecord.justification === 'string' ? outputRecord.justification : 'None';

  return (
    <div key={entry.id} className="space-y-1">
      <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">RESOURCE</p>
      <div>
        <p>
          <span className="text-sm text-slate-900 font-bold">Resource</span>:{' '}
          <span className="text-sm text-slate-800">{resourceName}</span>
        </p>
        <p>
          <span className="text-sm text-slate-900 font-bold">Justification </span>:{' '}
          <span className="text-sm text-slate-800">{justification}</span>
        </p>
      </div>
    </div>
  );
}

// Renders the agent trace structured event.
function AgentTraceStructuredEventEntry({ entry }: { entry: Extract<TraceEntry, { kind: 'action' }> }) {
  const payloadRecord = isRecord(entry.output) ? entry.output : null;
  const outputRecord = payloadRecord && isRecord(payloadRecord.result) ? payloadRecord.result : payloadRecord;
  const eventType =
    outputRecord && typeof outputRecord.event_type === 'string' ? outputRecord.event_type : 'structured_event';
  const step = outputRecord && typeof outputRecord.step === 'string' ? outputRecord.step : '';
  const summary = outputRecord && typeof outputRecord.summary === 'string' ? outputRecord.summary : '';
  const tag = outputRecord && typeof outputRecord.tag === 'string' ? outputRecord.tag : '';

  return (
    <div key={entry.id} className="space-y-1">
      <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">STRUCTURED THINKING</p>
      <p className="text-sm text-slate-900 font-semibold">{prettifyToolName(eventType)}</p>
      <div className="flex flex-wrap items-center flex-row">
        <p className="text-sm text-slate-800 font-semibold">Step :&nbsp;</p>
        <p className="text-sm text-slate-800">{truncateText(step || '—', 2000)}</p>
      </div>
      <div className="flex flex-wrap items-center flex-row">
        <p className="text-sm text-slate-800 font-semibold">Summary :&nbsp;</p>
        <p className="text-sm text-slate-800">{truncateText(summary || '—', 2000)}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2 mt-2 flex-row">
        <p className="text-sm text-slate-800">Tag:</p>
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="bg-PrimaryBlue/10 text-PrimaryBlue">{tag ? prettifyToolName(tag) : '—'}</Badge>
          <ToolStatusBadge status={entry.status} />
        </div>
      </div>
    </div>
  );
}

// Renders the agent trace action entry.
function AgentTraceActionEntry({ entry }: { entry: Extract<TraceEntry, { kind: 'action' }> }) {
  return (
    <div key={entry.id} className="space-y-2">
      <p className="text-xs font-semibold tracking-wide text-PrimaryBlue">ACTION</p>
      <p className="text-sm font-semibold text-slate-900">{prettifyToolName(entry.toolName)}</p>
      <div className="flex flex-wrap items-center gap-2">
        <ToolStatusBadge status={entry.status} />
        <TraceOutputHoverBadge value={entry.output} />
      </div>
    </div>
  );
}

// Renders the agent trace entries.
export function AgentTraceEntries({ entries }: { entries: TraceEntry[] }) {
  return (
    <div className="space-y-8 py-1">
      {entries.map((entry) => {
        if (entry.kind === 'action' && entry.toolName === 'create_plan') {
          return <AgentTracePlanEntry key={entry.id} entry={entry} />;
        }

        if (entry.kind === 'thinking') {
          return <AgentTraceThoughtEntry key={entry.id} entry={entry} />;
        }

        if (entry.kind === 'action' && entry.toolName === 'log_resource') {
          return <AgentTraceResourceEntry key={entry.id} entry={entry} />;
        }

        if (entry.kind === 'action' && entry.toolName === 'log_structured_event') {
          return <AgentTraceStructuredEventEntry key={entry.id} entry={entry} />;
        }

        return <AgentTraceActionEntry key={entry.id} entry={entry as Extract<TraceEntry, { kind: 'action' }>} />;
      })}
    </div>
  );
}
