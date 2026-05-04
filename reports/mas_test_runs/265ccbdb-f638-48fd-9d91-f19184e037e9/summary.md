# MAS Test Run Report: `265ccbdb-f638-48fd-9d91-f19184e037e9`

## Overview
- Report kind: `mas_test_run`
- Workflow: `esi_swarm_v1`
- Model: `medgemma-4b-it-llama`
- Status: `failed`
- Selected cases: `50`
- Swarm runs: `50`
- Case runs: `50`
- Succeeded case runs: `22`
- Failed case runs: `28`
- Success rate: `44.0%`
- Started: `2026-05-03T18:18:43.740305`
- Finished: `2026-05-03T18:54:48.342903`
- Duration (s): `2164.603`

## Agent Breakdown
- `doctor_agent`: runs=`45`, failed=`0`, succeeded=`45`, llm_calls=`90`, input_tokens=`152124`, output_tokens=`14780`
- `esi1_agent`: runs=`50`, failed=`1`, succeeded=`49`, llm_calls=`219`, input_tokens=`633619`, output_tokens=`32610`
- `esi2_agent`: runs=`34`, failed=`1`, succeeded=`33`, llm_calls=`166`, input_tokens=`472321`, output_tokens=`22195`
- `esi345_agent`: runs=`16`, failed=`0`, succeeded=`16`, llm_calls=`56`, input_tokens=`155255`, output_tokens=`9965`
- `vitals_agent`: runs=`50`, failed=`3`, succeeded=`47`, llm_calls=`227`, input_tokens=`670812`, output_tokens=`35257`

## Top Failure Classes
- `truncated_output`: `2`
- `schema_validation_error`: `2`
- `handoff_payload_invalid`: `1`

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
