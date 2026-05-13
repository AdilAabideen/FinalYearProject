# Frontend

## Overview

This project is a React, TypeScript, and Vite frontend for exploring and running single-agent and multi-agent workflows. The application is organized around a service-based architecture, where API access is isolated in dedicated service modules and UI logic is grouped by feature.

## Project Start Requirements

- Node.js
- npm
- A running backend environment if you want live data in the UI

## Start the Project

```bash
npm install
npm run dev
```

To create a production build:

```bash
npm run build
```

To preview the production build locally:

```bash
npm run preview
```

## Environment Configuration

The frontend uses Vite environment variables.

Create a `.env` file if you need to point the app to a specific backend:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If `VITE_API_BASE_URL` is not set, the app falls back to `http://127.0.0.1:8000`.

## Architecture

The codebase follows a service-based frontend structure:

- `src/services` contains API-facing service modules
- `src/features` contains feature-specific UI and state logic
- `src/shared` contains reusable UI and utility code
- `src/config` contains environment and application configuration
