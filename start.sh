#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/.proxy.pid"
LOG_FILE="/tmp/opencode-proxy.log"

PORT="${PROXY_PORT:-11434}"

# --- Try Docker first ---
if command -v docker &>/dev/null && docker compose version &>/dev/null 2>&1; then
    echo -e "${CYAN}Docker detected — using Docker Compose${NC}"
    cd "$PROJECT_DIR"
    docker compose up -d --build 2>&1 || {
        echo -e "${RED}Docker Compose failed. Check docker daemon.${NC}"
        exit 1
    }
    echo -e "${GREEN}Proxy running via Docker${NC}"
    echo "  → http://127.0.0.1:${PORT}"
    echo "  → docker compose logs -f"
    exit 0
fi

# --- Fallback to direct Python ---
echo -e "${YELLOW}Docker not available, falling back to direct Python${NC}"

if [[ -f "$PID_FILE" ]]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${GREEN}Proxy already running (PID: $pid)${NC}"
        echo "  http://127.0.0.1:${PORT}"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

cd "$PROJECT_DIR"
nohup python3 proxy-server.py > "$LOG_FILE" 2>&1 &
pid=$!
echo "$pid" > "$PID_FILE"

sleep 1.5

if kill -0 "$pid" 2>/dev/null; then
    echo -e "${GREEN}Proxy started (PID: $pid)${NC}"
    echo "  → http://127.0.0.1:${PORT}"
    echo "  → logs: $LOG_FILE"
else
    echo -e "${RED}Proxy failed to start. Check logs:${NC} $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
