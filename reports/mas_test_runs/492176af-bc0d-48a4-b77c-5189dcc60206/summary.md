# MAS Test Run Report: `492176af-bc0d-48a4-b77c-5189dcc60206`

## Overview
- Report kind: `mas_test_run`
- Workflow: `esi_swarm_v1`
- Model: `medgemma-4b-it-llama-tool`
- Status: `failed`
- Selected cases: `50`
- Swarm runs: `50`
- Case runs: `50`
- Succeeded case runs: `28`
- Failed case runs: `22`
- Success rate: `56.0%`
- Started: `2026-05-03T20:06:24.816855`
- Finished: `2026-05-03T20:46:13.541162`
- Duration (s): `2388.724`

## Agent Breakdown
- `doctor_agent`: runs=`47`, failed=`0`, succeeded=`47`, llm_calls=`94`, input_tokens=`158848`, output_tokens=`15379`
- `esi1_agent`: runs=`50`, failed=`1`, succeeded=`49`, llm_calls=`215`, input_tokens=`617646`, output_tokens=`32302`
- `esi2_agent`: runs=`32`, failed=`1`, succeeded=`31`, llm_calls=`155`, input_tokens=`447658`, output_tokens=`21228`
- `esi345_agent`: runs=`18`, failed=`0`, succeeded=`18`, llm_calls=`61`, input_tokens=`171793`, output_tokens=`11568`
- `vitals_agent`: runs=`50`, failed=`1`, succeeded=`48`, llm_calls=`264`, input_tokens=`997367`, output_tokens=`40444`

## Top Failure Classes
- `truncated_output`: `3`

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
