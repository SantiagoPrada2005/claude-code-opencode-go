#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/.proxy.pid"

if [[ -f "$PID_FILE" ]]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        sleep 0.5
        echo -e "${GREEN}Proxy stopped (was PID: $pid)${NC}"
    else
        echo -e "${YELLOW}Proxy not running (stale PID file)${NC}"
    fi
    rm -f "$PID_FILE"
else
    # Fallback: kill any proxy-server running on port 4000
    pids=$(pgrep -f "proxy-server.py" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        echo -e "${GREEN}Proxy stopped${NC}"
    else
        echo -e "${YELLOW}No proxy process found${NC}"
    fi
fi
