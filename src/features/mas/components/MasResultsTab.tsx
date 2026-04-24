type MasResultsTabProps = {
  input: Record<string, unknown>;
};

export default function MasResultsTab({ input }: MasResultsTabProps) {
  return (
    <div className="flex h-full min-h-[560px] items-center justify-center bg-white p-6">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
        <p className="text-sm font-semibold text-slate-900">MAS Results</p>
        <p className="mt-2 text-sm text-slate-500">
          Submitted workflow input is available here for the next rendering step.
        </p>
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <pre className="overflow-auto text-xs text-slate-700">
            {JSON.stringify(input, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
