#!/bin/bash
# Start both backend and frontend for development
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  ETF Central — Development Startup"
echo "============================================"
echo ""

# --- Backend ---
echo "==> Starting backend (port 8000)..."
cd "$PROJECT_DIR/backend"

if [ ! -d ".venv" ]; then
  echo "    Creating Python virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "    Created .env from .env.example"
fi

pip install -q -e "." 2>/dev/null
python main.py &
BACKEND_PID=$!
echo "    Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo "    Waiting for backend..."
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "    Backend ready."
    break
  fi
  sleep 1
done

# --- Seed workflow ---
echo ""
bash "$SCRIPT_DIR/seed-etf-workflow.sh"

# --- Frontend ---
echo ""
echo "==> Starting frontend (port 5173)..."
cd "$PROJECT_DIR/frontend"

if [ ! -d "node_modules" ]; then
  echo "    Installing npm packages..."
  npm install --silent
fi

npm run dev &
FRONTEND_PID=$!
echo "    Frontend PID: $FRONTEND_PID"

echo ""
echo "============================================"
echo "  Backend:  http://localhost:8000/docs"
echo "  Frontend: http://localhost:5173"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop both services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
