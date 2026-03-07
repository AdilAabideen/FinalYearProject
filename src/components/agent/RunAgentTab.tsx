import { useId, useState } from 'react';

type VitalsAgentInputFormState = {
  temperature: string;
  heartrate: string;
  resprate: string;
  o2sat: string;
  sbp: string;
  dbp: string;
  pain: string;
  subject_id: string;
  intime: string;
  chiefcomplaint: string;
  age_years: string;
};

export default function RunAgentTab() {
  const baseId = useId();
  const [form, setForm] = useState<VitalsAgentInputFormState>({
    temperature: '',
    heartrate: '',
    resprate: '',
    o2sat: '',
    sbp: '',
    dbp: '',
    pain: '',
    subject_id: '',
    intime: '',
    chiefcomplaint: '',
    age_years: '',
  });

  function setField<Key extends keyof VitalsAgentInputFormState>(key: Key, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const inputClassName =
    'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-PrimaryBlue focus-visible:ring-offset-2 focus-visible:ring-offset-white';

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">Run Agent</h3>
        <p className="mt-1 text-sm text-slate-600">
          Select tools and provide inputs to run this agent.
        </p>
        <p className="mt-1 text-xs font-semibold text-slate-500">VitalsAgentInput</p>
      </div>

      <div className="mt-4 space-y-6">
        <section aria-label="Vitals" className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-700">Vitals</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-temperature`}>
                Temperature
              </label>
              <input
                id={`${baseId}-temperature`}
                name="temperature"
                type="number"
                step="any"
                placeholder="e.g. 37.0"
                className={inputClassName}
                value={form.temperature}
                onChange={(e) => setField('temperature', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-heartrate`}>
                Heart Rate
              </label>
              <input
                id={`${baseId}-heartrate`}
                name="heartrate"
                type="number"
                step="any"
                placeholder="e.g. 82"
                className={inputClassName}
                value={form.heartrate}
                onChange={(e) => setField('heartrate', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-resprate`}>
                Resp Rate
              </label>
              <input
                id={`${baseId}-resprate`}
                name="resprate"
                type="number"
                step="any"
                placeholder="e.g. 16"
                className={inputClassName}
                value={form.resprate}
                onChange={(e) => setField('resprate', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-o2sat`}>
                O2 Sat
              </label>
              <input
                id={`${baseId}-o2sat`}
                name="o2sat"
                type="number"
                step="any"
                placeholder="e.g. 98"
                className={inputClassName}
                value={form.o2sat}
                onChange={(e) => setField('o2sat', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-sbp`}>
                SBP
              </label>
              <input
                id={`${baseId}-sbp`}
                name="sbp"
                type="number"
                step="any"
                placeholder="e.g. 120"
                className={inputClassName}
                value={form.sbp}
                onChange={(e) => setField('sbp', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-dbp`}>
                DBP
              </label>
              <input
                id={`${baseId}-dbp`}
                name="dbp"
                type="number"
                step="any"
                placeholder="e.g. 80"
                className={inputClassName}
                value={form.dbp}
                onChange={(e) => setField('dbp', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-pain`}>
                Pain
              </label>
              <input
                id={`${baseId}-pain`}
                name="pain"
                type="number"
                step="any"
                min={0}
                max={10}
                placeholder="0 - 10"
                className={inputClassName}
                value={form.pain}
                onChange={(e) => setField('pain', e.target.value)}
              />
            </div>
          </div>
        </section>

        <section aria-label="Patient context" className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-700">Patient</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-subject_id`}>
                Subject ID
              </label>
              <input
                id={`${baseId}-subject_id`}
                name="subject_id"
                type="number"
                step="1"
                placeholder="e.g. 123"
                className={inputClassName}
                value={form.subject_id}
                onChange={(e) => setField('subject_id', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-age_years`}>
                Age (years)
              </label>
              <input
                id={`${baseId}-age_years`}
                name="age_years"
                type="number"
                step="any"
                placeholder="e.g. 45"
                className={inputClassName}
                value={form.age_years}
                onChange={(e) => setField('age_years', e.target.value)}
              />
            </div>

            <div className="space-y-1 sm:col-span-2">
              <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-intime`}>
                In Time
              </label>
              <input
                id={`${baseId}-intime`}
                name="intime"
                type="datetime-local"
                className={inputClassName}
                value={form.intime}
                onChange={(e) => setField('intime', e.target.value)}
              />
            </div>

            <div className="space-y-1 sm:col-span-2">
              <label
                className="text-xs font-semibold text-slate-700"
                htmlFor={`${baseId}-chiefcomplaint`}
              >
                Chief Complaint
              </label>
              <textarea
                id={`${baseId}-chiefcomplaint`}
                name="chiefcomplaint"
                placeholder="Describe the chief complaint"
                className={`${inputClassName} min-h-24 resize-y`}
                value={form.chiefcomplaint}
                onChange={(e) => setField('chiefcomplaint', e.target.value)}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
