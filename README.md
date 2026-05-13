# ESI Multi-Agents SLM V Single Agent LLM

Multi-agent systems with small language models are a single-agent system with large language models.

This repository combines an Emergency Severity Index triage backend with a frontend for running and inspecting single-agent and multi-agent workflows.

## Repository Structure

- `backend/` contains the FastAPI backend for ESI inference, evaluation, run tracking, and test execution
- `frontend/` contains the React + TypeScript + Vite frontend
- `training_notebooks/` contains notebook-based model training and experimentation assets
- `Makefile` provides root-level commands for installing dependencies and running both services together
- Please See each project Readme for detailed explanation

## What The Project Does

The system takes a structured triage case as input and produces an ESI prediction.

The backend supports two execution modes:

- a single-agent baseline
- a configuration-driven multi-agent system built as a constrained LangGraph workflow

The backend exposes APIs for:

- starting single-agent runs
- starting multi-agent runs
- running single-agent test batches
- running multi-agent test batches
- streaming execution and test events over Server-Sent Events
- reading run outputs, metrics, and traces

The frontend is the interface for exploring those workflows and connecting to the backend APIs.

## Requirements

- Python 3.9+
- `pip`
- Node.js
- `npm`

## Setup

Install backend and frontend dependencies from the repo root:

```bash
make install
```

If you want to install each side manually:

```bash
cd backend && python3 -m pip install -r requirements.txt
cd frontend && npm install
```

## Backend Environment File

Create a `.env` file inside `backend/`.

If you want to run OpenAI-backed models, set:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

If you use Azure OpenAI instead of the standard OpenAI API, set:

```env
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=your_api_version
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
```

If you want MedGemma behind a self-hosted vLLM-compatible endpoint, the backend currently expects these legacy variable names:

```env
LLAMA_SERVER_BASE_URL=http://your-vllm-host:8000/v1
LLAMA_SERVER_API_KEY=your_optional_api_key
LLAMA_SERVER_SERIAL_REQUESTS=false
LLAMA_SERVER_TIMEOUT_S=60
```

If you want to use Doctor Seven / Dr7-hosted MedGemma, set:

```env
DR7_API_KEY=your_dr7_api_key
DR7_MEDICAL_BASE_URL=https://dr7.ai/api/v1/medical
```

The frontend can optionally use its own `.env` file in `frontend/`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If `VITE_API_BASE_URL` is not set, it falls back to `http://127.0.0.1:8000`.

## Running The Project

Run both services together from the repo root:

```bash
make run
```

Run them separately if needed:

```bash
make run-backend
make run-frontend
```

The backend starts on:

```text
http://localhost:8000
```

FastAPI docs are available at:

```text
http://localhost:8000/docs
```

The frontend runs through Vite in `frontend/`.

## Test Cases

On backend startup, the application seeds a small synthetic deidentified test set into the SQLite database by default:

- `10` fake single-agent test cases
- `10` fake multi-agent test cases

These are loaded from the backend seed files in `backend/app/`, including:

- [seed_agent_tests.py](/Users/adil/Documents/University/DIssFull/backend/app/seed_agent_tests.py:1)
- [seed_mas_tests.py](/Users/adil/Documents/University/DIssFull/backend/app/seed_mas_tests.py:1)
- [seed_mas_tests_esi_mas.jsonish](/Users/adil/Documents/University/DIssFull/backend/app/seed_mas_tests_esi_mas.jsonish:1)

The cases are synthetic and intended for development, regression checks, and evaluation workflows.

## Running Tests

Backend tests live under [backend/tests](/Users/adil/Documents/University/DIssFull/backend/tests:1) and are organized into:

- `unit/`
- `integration/`
- `regression/`
- `fixtures/`
- `helpers/`
- `doubles/`

Run the full backend test suite:

```bash
cd backend && pytest
```

Run only unit tests:

```bash
cd backend && pytest -m unit
```

Run integration tests:

```bash
cd backend && pytest -m integration
```

Run regression tests:

```bash
cd backend && pytest -m regression
```

The backend `pytest` configuration also defines markers for:

- `api`
- `db`
- `runtime`
- `wrapper`
- `telemetry`
- `agent_cases`
- `golden`
- `slow`
- `live_provider`

## Notebooks

Notebook assets live in [training_notebooks](/Users/adil/Documents/University/DIssFull/training_notebooks) and currently include:

- [ES1TrainingFinal.ipynb](/Users/adil/Documents/University/DIssFull/training_notebooks/ES1TrainingFinal.ipynb)
- [ES3Training.ipynb](/Users/adil/Documents/University/DIssFull/training_notebooks/ES3Training.ipynb)
- [ESI2TrainingFinalipynb.ipynb](/Users/adil/Documents/University/DIssFull/training_notebooks/ESI2TrainingFinalipynb.ipynb)
- [MedGemmaToolAceTraining.ipynb](/Users/adil/Documents/University/DIssFull/training_notebooks/MedGemmaToolAceTraining.ipynb)

These notebooks sit alongside the application code and test suite as part of the wider project workflow.

## Backend Notes

When the backend starts, it:

- creates database tables if they do not exist
- applies runtime schema upgrades
- seeds the deidentified single-agent and multi-agent test cases

By default the backend database is:

```text
backend/app.db
```

The backend model registry is defined in [backend/app/agentic/model_registry.py](/Users/adil/Documents/University/DIssFull/backend/app/agentic/model_registry.py:1).

If you want to point the backend at your own hosted model endpoint, the main files to inspect are:

- [backend/app/config.py](/Users/adil/Documents/University/DIssFull/backend/app/config.py:1)
- [backend/app/agentic/model_registry.py](/Users/adil/Documents/University/DIssFull/backend/app/agentic/model_registry.py:1)
- [backend/app/agentic/models/vllm_chat.py](/Users/adil/Documents/University/DIssFull/backend/app/agentic/models/vllm_chat.py:1)
- [backend/app/agentic/models/medgemma_medical_chat.py](/Users/adil/Documents/University/DIssFull/backend/app/agentic/models/medgemma_medical_chat.py:1)

## API Surface

The main backend test execution endpoints are:

- `POST /api/tests/runs/start` for single-agent batch tests
- `GET /api/tests/runs/{run_id}/stream` for single-agent test streaming
- `POST /api/mas-tests/runs/start` for multi-agent batch tests
- `GET /api/mas-tests/runs/{run_id}/stream` for multi-agent test streaming

Operational run endpoints are mounted under:

- `/api/agent-runs`
- `/api/mas-runs`

There is also a compatibility alias for:

- `/api/swarm-runs`

