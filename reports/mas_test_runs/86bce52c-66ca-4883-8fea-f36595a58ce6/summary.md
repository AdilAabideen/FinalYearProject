# MAS Test Run Report: `86bce52c-66ca-4883-8fea-f36595a58ce6`

## Overview
- Report kind: `mas_test_run`
- Workflow: `esi_swarm_v1`
- Model: `medgemma-4b-it-Finetuned`
- Status: `failed`
- Selected cases: `50`
- Swarm runs: `50`
- Case runs: `50`
- Succeeded case runs: `32`
- Failed case runs: `18`
- Success rate: `64.0%`
- Started: `2026-05-03T22:33:39.304360`
- Finished: `2026-05-03T23:09:52.520962`
- Duration (s): `2173.217`

## Agent Breakdown
- `doctor_agent`: runs=`48`, failed=`0`, succeeded=`48`, llm_calls=`96`, input_tokens=`162240`, output_tokens=`15687`
- `esi1_agent`: runs=`50`, failed=`0`, succeeded=`50`, llm_calls=`213`, input_tokens=`615830`, output_tokens=`31832`
- `esi2_agent`: runs=`25`, failed=`0`, succeeded=`25`, llm_calls=`123`, input_tokens=`351435`, output_tokens=`15602`
- `esi345_agent`: runs=`15`, failed=`0`, succeeded=`15`, llm_calls=`55`, input_tokens=`152999`, output_tokens=`9464`
- `vitals_agent`: runs=`50`, failed=`2`, succeeded=`48`, llm_calls=`226`, input_tokens=`666773`, output_tokens=`34734`

## Top Failure Classes
- `handoff_payload_invalid`: `1`
- `truncated_output`: `1`

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
