#!/usr/bin/env bash
# One-click start for the Driver Monitor POC demo: backend + UI + seeded sample data.
#
# Sets up (if needed) and starts dms-backend and dms-ui, waits for the backend
# to come up, then runs dms-backend/scripts/seed_demo.py to populate the
# dashboard with sample violations. Does NOT start dms-edge (that needs a real
# video file / camera and is run separately -- see demo/DEMO_GUIDE.md).
#
# Safe to re-run: reuses existing virtualenvs/node_modules instead of recreating them.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$REPO_ROOT/dms-backend"
UI_DIR="$REPO_ROOT/dms-ui"
PID_FILE="$SCRIPT_DIR/.demo_pids"

step() { echo -e "\n==> $1"; }
ok()   { echo "    $1"; }
warn() { echo "    $1"; }

# ---------------------------------------------------------------------------
# 1. Prerequisite checks
# ---------------------------------------------------------------------------
step "Checking prerequisites"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Install Python 3.11+ and re-run." >&2
    exit 1
fi
PY_VERSION="$(python3 --version)"
ok "$PY_VERSION"

if ! command -v node >/dev/null 2>&1; then
    echo "ERROR: node not found. Install Node 18+ (20+ recommended) and re-run." >&2
    exit 1
fi
ok "Node $(node --version)"

# ---------------------------------------------------------------------------
# 2. Backend: venv + install + start
# ---------------------------------------------------------------------------
step "Setting up dms-backend"

BACKEND_VENV="$BACKEND_DIR/.venv"
if [ ! -d "$BACKEND_VENV" ]; then
    warn "Creating virtual environment (first run only)..."
    python3 -m venv "$BACKEND_VENV"
fi

BACKEND_PIP="$BACKEND_VENV/bin/pip"
BACKEND_PY="$BACKEND_VENV/bin/python"

warn "Installing/verifying dependencies..."
"$BACKEND_PIP" install -q -r "$BACKEND_DIR/requirements.txt"
ok "Backend dependencies ready"

step "Starting dms-backend on http://localhost:8000"
(
    cd "$BACKEND_DIR"
    nohup "$BACKEND_PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
        > "$SCRIPT_DIR/backend.log" 2> "$SCRIPT_DIR/backend.err.log" &
    echo $! > "$SCRIPT_DIR/.backend.pid"
)
BACKEND_PID="$(cat "$SCRIPT_DIR/.backend.pid")"
ok "Backend process started (PID $BACKEND_PID), logs at demo/backend.log"

# ---------------------------------------------------------------------------
# 3. UI: npm install + start
# ---------------------------------------------------------------------------
step "Setting up dms-ui"

if [ ! -d "$UI_DIR/node_modules" ]; then
    warn "Running npm install (first run only)..."
    (cd "$UI_DIR" && npm install)
fi
ok "UI dependencies ready"

step "Starting dms-ui on http://localhost:5173"
(
    cd "$UI_DIR"
    nohup npm run dev > "$SCRIPT_DIR/ui.log" 2> "$SCRIPT_DIR/ui.err.log" &
    echo $! > "$SCRIPT_DIR/.ui.pid"
)
UI_PID="$(cat "$SCRIPT_DIR/.ui.pid")"
ok "UI process started (PID $UI_PID), logs at demo/ui.log"

cat > "$SCRIPT_DIR/.demo_pids" <<EOF
backend=$BACKEND_PID
ui=$UI_PID
EOF
rm -f "$SCRIPT_DIR/.backend.pid" "$SCRIPT_DIR/.ui.pid"

# ---------------------------------------------------------------------------
# 4. Wait for backend to respond
# ---------------------------------------------------------------------------
step "Waiting for backend to become ready"
READY=0
for _ in $(seq 1 30); do
    if curl -fsS "http://localhost:8000/" >/dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done
if [ "$READY" -ne 1 ]; then
    echo "ERROR: Backend did not become ready within 30s. Check demo/backend.err.log for details." >&2
    exit 1
fi
ok "Backend is up"

# ---------------------------------------------------------------------------
# 5. Seed sample data
# ---------------------------------------------------------------------------
step "Seeding sample violations (drowsiness, phone use, distraction, continuous drive)"
if (cd "$BACKEND_DIR" && "$BACKEND_PY" scripts/seed_demo.py); then
    ok "Sample data injected"
else
    warn "Seed script exited with an error -- the backend/UI are still running, check demo/backend.err.log."
fi

# ---------------------------------------------------------------------------
# 6. Done
# ---------------------------------------------------------------------------
echo ""
echo "================================================================"
echo " Dashboard:  http://localhost:5173"
echo " Backend API docs: http://localhost:8000/docs"
echo " To stop everything:  ./demo/stop_demo.sh"
echo "================================================================"
