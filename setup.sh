#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Claude Code + OpenCode Go — Setup                 ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# --- Check Python ---
echo -e "${YELLOW}[1/4] Checking Python...${NC}"
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(sys.version_info[:2])" 2>/dev/null || echo "(0,0)")
        if [[ "$ver" == "(3,"* ]]; then
            PYTHON="$cmd"; break
        fi
    fi
done
if [[ -z "$PYTHON" ]]; then
    echo -e "${RED}Python 3.9+ required. Install it first.${NC}"; exit 1
fi
echo -e "  ${GREEN}✓${NC} Found $($PYTHON --version)"

# --- Install dependencies ---
echo -e "${YELLOW}[2/4] Installing dependencies...${NC}"
$PYTHON -m pip install fastapi httpx uvicorn --quiet --user 2>/dev/null || \
    $PYTHON -m pip install fastapi httpx uvicorn --quiet --break-system-packages 2>/dev/null || {
    echo -e "${RED}Failed to install Python packages. Try manually:${NC}"
    echo "  pip3 install fastapi httpx uvicorn --user"
    exit 1
}
echo -e "  ${GREEN}✓${NC} fastapi, httpx, uvicorn installed"

# --- API Key ---
echo -e "${YELLOW}[3/4] OpenCode Go API key${NC}"
ENV_FILE="$PROJECT_DIR/.env"
if [[ -f "$ENV_FILE" ]] && grep -q "OPENCODE_API_KEY=sk-" "$ENV_FILE" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} .env already configured"
else
    echo ""
    echo -e "  Get your key at: ${CYAN}https://opencode.ai/auth${NC}"
    echo ""
    read -rsp "  Paste your OpenCode Go API key: " api_key
    echo ""
    if [[ -z "$api_key" ]]; then
        echo -e "  ${YELLOW}Skipped. Set it later in .env or export OPENCODE_API_KEY${NC}"
    else
        echo "OPENCODE_API_KEY=$api_key" > "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        echo -e "  ${GREEN}✓${NC} Saved to .env"
    fi
fi

# --- Claude Code settings ---
echo -e "${YELLOW}[4/4] Claude Code settings${NC}"
SETTINGS_FILE="$HOME/.claude/settings.json"

if [[ -f "$SETTINGS_FILE" ]]; then
    if grep -q "localhost:4000" "$SETTINGS_FILE" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Already configured"
    else
        echo ""
        echo -e "  ${YELLOW}Add this to your ${CYAN}~/.claude/settings.json${YELLOW} under \"env\":${NC}"
        echo ""
        echo -e '  {'
        echo -e '    "env": {'
        echo -e '      "ANTHROPIC_API_KEY": "any-key",'
        echo -e '      "ANTHROPIC_BASE_URL": "http://localhost:4000",'
        echo -e '      "ANTHROPIC_MODEL": "deepseek-v4-pro",'
        echo -e '      "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek-v4-pro",'
        echo -e '      "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro",'
        echo -e '      "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",'
        echo -e '      "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",'
        echo -e '      "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "true"'
        echo -e '    }'
        echo -e '  }'
        echo ""
    fi
else
    echo -e "  ${YELLOW}~/.claude/settings.json not found. Create it with:${NC}"
    echo '  mkdir -p ~/.claude && echo '"'"'{"env":{"ANTHROPIC_API_KEY":"any-key","ANTHROPIC_BASE_URL":"http://localhost:4000","ANTHROPIC_MODEL":"deepseek-v4-pro","CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS":"true"}}'"'"' > ~/.claude/settings.json'
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup complete!                                      ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Start the proxy:   ./start.sh                        ║${NC}"
echo -e "${GREEN}║  Then open Claude:  claude                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
