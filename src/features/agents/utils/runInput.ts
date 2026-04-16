import type { AgentCatalogDetail } from '../../../types/agents';
import { getPrimaryType, getStringFormat, isRecord } from './jsonSchema';

const ESI1_TRIAGE_CASE =
  'A 63-year-old male with a history of aortic regurgitation, mechanical aortic valve placement, ascending aortic aneurysm repair, diabetes, hypertension, and hyperlipidemia presents to the ED via ambulance with a chief complaint of palpitations and dizziness. On arrival, vital signs were absent, indicating a potential cardiac emergency. The patient has a history of ventricular tachycardia and recent ICD placement. For the past two days, he experienced lightheadedness, resolving initially but recurring last night. He denies recent chest pain, fever, cough, leg pain, swelling, abdominal pain, nausea, or vomiting. He has no known allergies. Immediate resuscitation with ACLS measures is required.';

const DEFAULT_INPUTS_BY_AGENT: Record<string, Record<string, unknown>> = {
  vitals_agent: {
    temperature: '98.3',
    heartrate: '75',
    resprate: '14',
    o2sat: '100',
    sbp: '138',
    dbp: '90',
    pain: '7',
    subject_id: '19880634',
    intime: '2199-10-08T16:40',
    age_years: '49.7',
    chiefcomplaint: 'Left Abdominal Pain',
  },
  esi1_agent: {
    stay_id: '31731173',
    subject_id: '16307504',
    hadm_id: '23603634',
    intime: '2158-10-24T03:35',
    outtime: '2158-10-24T08:58',
    gender: 'M',
    race: 'WHITE',
    arrival_transport: 'AMBULANCE',
    disposition: 'ADMITTED',
    temperature: '0',
    heartrate: '0',
    resprate: '0',
    o2sat: '0',
    sbp: '0',
    dbp: '0',
    pain: '0',
    chiefcomplaint: 'Chest pain',
    invasive_ventilation: '0',
    invasive_ventilation_beyond_1h: '0',
    non_invasive_ventilation: '0',
    transfer2surgeryin1h: '0',
    transfer_to_surgery_beyond_1h: '0',
    transfer_to_icu_in_1h: '1',
    transfer_to_icu_beyond_1h: '0',
    transfer_within_1h: '0',
    transfer_beyond_1h: '0',
    expired_within_1h: '0',
    expired_beyond_1h: '0',
    tier1_med_usage_1h: '0',
    tier1_med_usage_beyond_1h: '0',
    tier2_med_usage: '0',
    tier3_med_usage: '0',
    tier4_med_usage: '0',
    psychotropic_med_within_120min: '0',
    transfusion_within_1h: '0',
    transfusion_beyond_1h: '0',
    red_cell_order_more_than_1: '0',
    intraosseous_line_placed: '0',
    critical_procedure: '6',
    lab_event_count: '2',
    microbio_event_count: '2',
    exam_count: '0',
    intravenous_fluids: '0',
    intravenous: '0',
    intramuscular: '0',
    nebulized_medications: '0',
    oral_medications: '0',
    consults_count: '0',
    procedure_count: '1',
    age: '63.8',
    resources_used: '10',
    tiragecase: ESI1_TRIAGE_CASE,
    triagecase: ESI1_TRIAGE_CASE,
    'Expert 1 Opinion': 'AGREE',
    'Expert 2 Opinion': 'AGREE',
    'Expert 3 Opinion': '',
    expert_1_opinion: 'AGREE',
    expert_2_opinion: 'AGREE',
    expert_3_opinion: '',
    acuity: '1',
    'Final Decision': 'RETAIN',
    final_decision: 'RETAIN',
  },
};

export function getDefaultInputs(agent: AgentCatalogDetail): Record<string, unknown> {
  const defaults = DEFAULT_INPUTS_BY_AGENT[agent.name];
  return defaults ? { ...defaults } : {};
}

export function coerceInputForRun(inputSchema: Record<string, unknown>, raw: Record<string, unknown>) {
  const properties = isRecord(inputSchema.properties) ? inputSchema.properties : {};
  const required = new Set(
    Array.isArray(inputSchema.required)
      ? inputSchema.required.filter((k): k is string => typeof k === 'string' && k.length > 0)
      : [],
  );

  const output: Record<string, unknown> = {};

  for (const [key, schema] of Object.entries(properties)) {
    const rawValue = raw[key];

    if (rawValue == null || rawValue === '') {
      if (required.has(key)) throw new Error(`Missing required field: ${key}`);
      continue;
    }

    const primaryType = getPrimaryType(inputSchema, schema);
    const stringFormat = getStringFormat(inputSchema, schema);

    if ((primaryType === 'number' || primaryType === 'integer') && typeof rawValue === 'string') {
      const num = Number(rawValue);
      if (!Number.isFinite(num)) throw new Error(`Invalid number for ${key}`);
      output[key] = primaryType === 'integer' ? Math.trunc(num) : num;
      continue;
    }

    if (primaryType === 'integer' && typeof rawValue === 'number') {
      output[key] = Math.trunc(rawValue);
      continue;
    }

    if (primaryType === 'number' && typeof rawValue === 'number') {
      output[key] = rawValue;
      continue;
    }

    if (primaryType === 'string' && stringFormat === 'date-time' && typeof rawValue === 'string') {
      output[key] = rawValue;
      continue;
    }

    output[key] = rawValue;
  }

  return output;
}
