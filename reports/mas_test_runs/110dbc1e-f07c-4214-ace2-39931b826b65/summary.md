# MAS Test Run Report: `110dbc1e-f07c-4214-ace2-39931b826b65`

## Overview
- Report kind: `mas_test_run`
- Workflow: `esi_swarm_v1`
- Model: `medgemma-4b-it-Finetuned`
- Status: `failed`
- Selected cases: `50`
- Swarm runs: `50`
- Case runs: `50`
- Succeeded case runs: `26`
- Failed case runs: `24`
- Success rate: `52.0%`
- Started: `2026-05-03T21:32:17.490379`
- Finished: `2026-05-03T22:08:46.164019`
- Duration (s): `2188.674`

## Agent Breakdown
- `doctor_agent`: runs=`48`, failed=`0`, succeeded=`48`, llm_calls=`96`, input_tokens=`162440`, output_tokens=`15746`
- `esi1_agent`: runs=`50`, failed=`0`, succeeded=`50`, llm_calls=`219`, input_tokens=`634539`, output_tokens=`32118`
- `esi2_agent`: runs=`24`, failed=`2`, succeeded=`22`, llm_calls=`115`, input_tokens=`325469`, output_tokens=`14563`
- `esi345_agent`: runs=`16`, failed=`0`, succeeded=`16`, llm_calls=`55`, input_tokens=`151482`, output_tokens=`9461`
- `vitals_agent`: runs=`50`, failed=`0`, succeeded=`50`, llm_calls=`230`, input_tokens=`681143`, output_tokens=`35387`

## Top Failure Classes
- `truncated_output`: `2`

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
