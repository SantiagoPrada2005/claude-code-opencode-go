# Claude Code + OpenCode Go

Usa Claude Code con modelos de OpenCode Go (`deepseek-v4-pro`, `deepseek-v4-flash`, etc.) via un proxy local que traduce Anthropic Messages API → OpenAI Chat Completions.

## Arquitectura

```
Claude Code ── Anthropic API ──→ Proxy (localhost:4000) ── OpenAI API ──→ OpenCode Go
                                    proxy-server.py                     zen/go/v1/chat/completions
```

## Requisitos

- Python 3.9+
- Claude Code instalado
- API key de OpenCode Go (suscríbete en [opencode.ai](https://opencode.ai))

## Instalación (1 minuto)

```bash
# 1. Clonar este repo
git clone <repo-url> ~/claude-code-opencode-go

# 2. Instalar dependencias Python
pip3 install fastapi httpx uvicorn --user

# 3. Setear tu API key de OpenCode Go
export OPENCODE_API_KEY="sk-..."

# 4. Iniciar el proxy
nohup python3 ~/claude-code-opencode-go/proxy-server.py > /tmp/proxy.log 2>&1 &

# 5. Verificar que corre
curl http://localhost:4000/health
# → {"status":"ok"}
```

## Configurar Claude Code

Agregar al `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "any-key",
    "ANTHROPIC_BASE_URL": "http://localhost:4000",
    "ANTHROPIC_MODEL": "deepseek-v4-pro",
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "true"
  }
}
```

Abrir `claude` en cualquier proyecto y listo.

## Endpoints del proxy

| Endpoint | Uso |
|----------|-----|
| `POST /v1/messages` | Anthropic Messages API (chat, tools, streaming) |
| `POST /v1/messages/count_tokens` | Conteo de tokens |
| `GET /v1/models` | Lista de modelos disponibles |
| `GET /health` | Health check |

## Modelos disponibles en OpenCode Go

```
deepseek-v4-pro   deepseek-v4-flash
kimi-k2.6         kimi-k2.5
glm-5.1           glm-5
qwen3.6-plus      qwen3.5-plus
mimo-v2-pro       mimo-v2-omni
mimo-v2.5-pro     mimo-v2.5
minimax-m2.7      minimax-m2.5
```

Para usar otro modelo, agrégalo al `list_models()` en `proxy-server.py` y actualiza `settings.json`.

## Comandos útiles

```bash
# Iniciar proxy
export OPENCODE_API_KEY="sk-..."
nohup python3 ~/claude-code-opencode-go/proxy-server.py > /tmp/proxy.log 2>&1 &

# Detener proxy
pkill -f proxy-server

# Ver logs
tail -f /tmp/proxy.log
```

## Revertir a DeepSeek directo

```json
"ANTHROPIC_API_KEY": "sk-87c2912b14ce4fc292b460760ab1d149",
"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic"
```

Quitar `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`.

## Limitaciones

- **Token counting aproximado** (word-based ×2). Precisión suficiente para gestión de contexto.
- **DeepSeek v4 pro thinking mode** puede consumir tokens en razonamiento con `max_tokens` bajo.
- **Sin autenticación** en el proxy — solo exponer en localhost.
- **Dependencias mínimas**: fastapi, httpx, uvicorn.

## Licencia

MIT
