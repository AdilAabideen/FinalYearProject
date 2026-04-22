import type { ModelSpec } from '../../../../types/models';

type AgentModelSelectProps = {
  id: string;
  labelClassName?: string;
  selectClassName?: string;
  models: ModelSpec[];
  modelsStatus: 'loading' | 'error' | 'success';
  selectedModelId: string;
  setSelectedModelId: (value: string) => void;
  disabled?: boolean;
};

export function AgentModelSelect({
  id,
  labelClassName = 'text-xs font-semibold text-slate-700',
  selectClassName,
  models,
  modelsStatus,
  selectedModelId,
  setSelectedModelId,
  disabled = false,
}: AgentModelSelectProps) {
  return (
    <>
      <label htmlFor={id} className={labelClassName}>
        Model
      </label>
      <select
        id={id}
        value={selectedModelId}
        onChange={(e) => setSelectedModelId(e.target.value)}
        disabled={disabled || modelsStatus !== 'success' || models.length === 0}
        className={
          selectClassName ??
          'min-w-48 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400'
        }
      >
        {modelsStatus === 'loading' ? <option value="">Loading…</option> : null}
        {modelsStatus === 'error' ? <option value="">Unavailable</option> : null}
        {modelsStatus === 'success'
          ? models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.id} ({model.provider})
              </option>
            ))
          : null}
      </select>
    </>
  );
}
