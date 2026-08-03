#!/usr/bin/env bash
# Stops the backend and UI processes started by demo/start_demo.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.demo_pids"

if [ ! -f "$PID_FILE" ]; then
    echo "No record of a running demo (missing demo/.demo_pids). Nothing to stop."
    exit 0
fi

# shellcheck disable=SC1090
source "$PID_FILE"

for entry in "backend:${backend:-}" "ui:${ui:-}"; do
    name="${entry%%:*}"
    pid="${entry#*:}"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null
        echo "Stopped $name (PID $pid)"
    else
        echo "$name (PID ${pid:-unknown}) was not running"
    fi
done

rm -f "$PID_FILE"
echo "Done."
