# FinalYearProject

This repository combines the backend and frontend projects while preserving the commit history of both source repositories.

## Structure

- `backend/` contains the FastAPI backend imported via `git subtree`
- `frontend/` contains the React/Vite frontend imported via `git subtree`

## Root Commands

Install dependencies for both projects:

```bash
make install
```

Run backend and frontend together:

```bash
make run
```

Run each side separately:

```bash
make run-backend
make run-frontend
```
