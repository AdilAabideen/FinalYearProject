import type { MasTestCaseRead } from '../../../types/masTests';
import { formatMasDateTime } from '../utils/format';
import type { ModelSpec } from '../../../types/models';
import { AgentModelSelect } from '../../agents/components/shared/AgentModelSelect';

type MasTestCaseSelectionPanelProps = {
  testCases: MasTestCaseRead[];
  selectedTestCaseIds: string[];
  allSelected: boolean;
  modelSelectId: string;
  modelsStatus: 'loading' | 'error' | 'success';
  models: ModelSpec[];
  selectedModelId: string;
  setSelectedModelId: (value: string) => void;
  onToggleAll: () => void;
  onToggleOne: (testCaseId: string) => void;
  onOpenSelectedCases: () => void;
};

export function MasTestCaseSelectionPanel({
  testCases,
  selectedTestCaseIds,
  allSelected,
  onToggleAll,
  onToggleOne,
  onOpenSelectedCases,
  modelSelectId,
  modelsStatus,
  models,
  selectedModelId,
  setSelectedModelId
}: MasTestCaseSelectionPanelProps) {
  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div className='w-full flex flex-row justify-between'>
        <div className="border-b border-slate-200 px-6 py-4">
          <p className="text-lg font-semibold text-slate-900">Select Test Cases</p>
          <p className="mt-1 text-sm text-slate-500">
            Choose the cases you want to inspect before opening the workspace.
          </p>
        </div>
        <div className='flex flex-row gap-1 items-center px-8'>
          <AgentModelSelect
            id={modelSelectId}
            models={models}
            modelsStatus={modelsStatus}
            selectedModelId={selectedModelId}
            setSelectedModelId={setSelectedModelId}
          />
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <div className="h-full overflow-auto rounded border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <label className="inline-flex items-center gap-2 normal-case tracking-normal text-slate-600">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={onToggleAll}
                      className="h-4 w-4 rounded border-slate-300 text-PrimaryBlue focus:ring-PrimaryBlue"
                    />
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Select All
                    </span>
                  </label>
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Created
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Updated
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {testCases.map((testCase) => {
                const checked = selectedTestCaseIds.includes(testCase.id);

                return (
                  <tr key={testCase.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => onToggleOne(testCase.id)}
                        className="h-4 w-4 rounded border-slate-300 text-PrimaryBlue focus:ring-PrimaryBlue"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-900">{testCase.name}</td>
                    <td className="px-4 py-3">
                      <span
                        className={[
                          'inline-flex rounded-full border px-3 py-1 text-xs font-semibold',
                          testCase.enabled
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : 'border-slate-200 bg-slate-50 text-slate-600',
                        ].join(' ')}
                      >
                        {testCase.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {formatMasDateTime(testCase.createdAt)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {formatMasDateTime(testCase.updatedAt)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-slate-200 bg-white px-6 py-4">
        <p className="text-sm text-slate-500">
          {selectedTestCaseIds.length} {selectedTestCaseIds.length === 1 ? 'case' : 'cases'} selected
        </p>
        <button
          type="button"
          disabled={selectedTestCaseIds.length === 0}
          onClick={onOpenSelectedCases}
          className={[
            'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold transition',
            selectedTestCaseIds.length === 0
              ? 'cursor-not-allowed bg-slate-100 text-slate-400'
              : 'bg-PrimaryBlue text-white hover:bg-PrimaryBlue/90',
          ].join(' ')}
        >
          Open Selected Cases
        </button>
      </div>
    </div>
  );
}
