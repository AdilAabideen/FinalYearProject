const friendlyLabels: Record<string, string> = {
  age_years: 'Age',
  chiefcomplaint: 'Chief Complaint',
  dbp: 'DBP',
  heartrate: 'Heart Rate',
  intime: 'Intime',
  o2sat: 'O₂ Sat',
  pain: 'Pain',
  resprate: 'Resp Rate',
  sbp: 'SBP',
  temperature: 'Temperature',
  subject_id: 'Subject ID',
};

// Renders the case badge.
export function CaseBadge({ label, value }: { label: string; value: string | number }) {
  const display = friendlyLabels[label] ?? label;
  return (
    <span className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-700">
      {display}: {value}
    </span>
  );
}
