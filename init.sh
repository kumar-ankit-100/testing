#!/bin/bash
set -euo pipefail

echo "=== Bootstrapping dev environment ==="

# Backend dependencies
cd backend && uv sync && cd ..

# Frontend dependencies
cd frontend && npm ci && cd ..

# Environment
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your API keys"
fi

# Start local dev servers
echo "Starting backend on http://localhost:8000 ..."
(cd backend && uv run uvicorn app.api.main:app --reload --port 8000 &)

echo "Starting frontend on http://localhost:5173 ..."
(cd frontend && npm run dev &)

# Health checks
echo "Waiting for services..."
curl --retry 5 --retry-delay 2 --retry-connrefused -sf http://localhost:8000/health || echo "backend health check failed"
curl --retry 5 --retry-delay 2 --retry-connrefused -sf http://localhost:5173 || echo "frontend health check failed"

echo "=== Environment ready ==="
