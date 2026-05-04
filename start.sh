#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/.proxy.pid"
LOG_FILE="/tmp/opencode-proxy.log"

# Check if already running
if [[ -f "$PID_FILE" ]]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${GREEN}Proxy already running (PID: $pid)${NC}"
        echo "  http://localhost:4000"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# Start proxy
cd "$PROJECT_DIR"
nohup python3 proxy-server.py > "$LOG_FILE" 2>&1 &
pid=$!
echo "$pid" > "$PID_FILE"

sleep 1.5

if kill -0 "$pid" 2>/dev/null; then
    echo -e "${GREEN}Proxy started (PID: $pid)${NC}"
    echo "  → http://localhost:4000"
    echo "  → logs: $LOG_FILE"
else
    echo -e "${RED}Proxy failed to start. Check logs:${NC} $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
