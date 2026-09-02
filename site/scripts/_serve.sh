#!/usr/bin/env bash
# Serve the static export for QA. Usage: scripts/_serve.sh [port]
PORT=${1:-3100}
SCRATCH="${TMPDIR:-/tmp}"
if [ -f "$SCRATCH/bench-server.pid" ]; then kill "$(cat $SCRATCH/bench-server.pid)" 2>/dev/null; sleep 1; fi
fuser -k "$PORT"/tcp 2>/dev/null; sleep 1
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
nohup node scripts/_static-server.mjs "$PORT" > "$SCRATCH/bench-server.log" 2>&1 &
echo $! > "$SCRATCH/bench-server.pid"
for i in $(seq 1 20); do sleep 0.5; curl -s -o /dev/null "http://localhost:$PORT/" && break; done
curl -s -o /dev/null -w "server up: %{http_code}\n" "http://localhost:$PORT/"
