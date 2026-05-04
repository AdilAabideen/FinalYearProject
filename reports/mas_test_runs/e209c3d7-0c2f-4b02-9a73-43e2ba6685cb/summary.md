# MAS Test Run Report: `e209c3d7-0c2f-4b02-9a73-43e2ba6685cb`

## Overview
- Report kind: `mas_test_run`
- Workflow: `esi_swarm_v1`
- Model: `gemma-3-4b-it`
- Status: `failed`
- Selected cases: `50`
- Swarm runs: `50`
- Case runs: `50`
- Succeeded case runs: `20`
- Failed case runs: `30`
- Success rate: `40.0%`
- Started: `2026-05-03T23:21:13.595152`
- Finished: `2026-05-03T23:53:28.657957`
- Duration (s): `1935.063`

## Agent Breakdown
- `doctor_agent`: runs=`49`, failed=`0`, succeeded=`49`, llm_calls=`49`, input_tokens=`76422`, output_tokens=`5157`
- `esi1_agent`: runs=`50`, failed=`0`, succeeded=`50`, llm_calls=`235`, input_tokens=`664578`, output_tokens=`26317`
- `esi2_agent`: runs=`19`, failed=`0`, succeeded=`19`, llm_calls=`92`, input_tokens=`248699`, output_tokens=`9380`
- `esi345_agent`: runs=`16`, failed=`0`, succeeded=`16`, llm_calls=`72`, input_tokens=`199815`, output_tokens=`8647`
- `vitals_agent`: runs=`50`, failed=`1`, succeeded=`49`, llm_calls=`319`, input_tokens=`953902`, output_tokens=`33856`

## Top Failure Classes
- `schema_validation_error`: `1`

## Files
- `mas_test_run.csv`
- `mas_test_case_runs.csv`
- `swarm_runs.csv`
- `swarm_run_metrics.csv`
- `swarm_events.csv`
- `swarm_handoffs.csv`
- `swarm_final_outputs.csv`
- `agent_runs.csv`
- `agent_events.csv`
- `agent_llm_calls.csv`
- `tool_calls.csv`
- `metrics_rollup.csv`
