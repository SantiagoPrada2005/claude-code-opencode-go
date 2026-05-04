#!/usr/bin/env python3
"""
Anthropic Messages API → OpenAI Chat Completions API proxy.
Bridges Claude Code (Anthropic format) to OpenCode Go (OpenAI format).
"""
import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse

# Load .env file if present
_ENV_FILE = Path(__file__).resolve().parent / ".env"
if _ENV_FILE.exists():
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = val

OPENCODE_API_KEY = os.environ.get("OPENCODE_API_KEY")
if not OPENCODE_API_KEY:
    raise RuntimeError(
        "OPENCODE_API_KEY not set. Create a .env file or export the env var.\n"
        "  cp .env.example .env  # then edit .env with your key"
    )

OPENCODE_BASE = os.environ.get(
    "OPENCODE_BASE_URL",
    "https://opencode.ai/zen/go/v1/chat/completions"
)

PROXY_HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "11434"))

AVAILABLE_MODELS = os.environ.get(
    "AVAILABLE_MODELS",
    "deepseek-v4-pro,deepseek-v4-flash"
)

app = FastAPI()


def _extract_text(content):
    """Extract plain text from Anthropic content (string or list of blocks)."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "image_url":
                parts.append("[image]")
    return "\n".join(parts)


def anthropic_messages_to_openai(body: dict) -> dict:
    """Convert Anthropic Messages API request to OpenAI Chat Completions."""
    oai_messages = []

    system = body.get("system")
    if system:
        if isinstance(system, list):
            system_text = "\n".join(
                s.get("text", "") for s in system if s.get("type") == "text"
            )
        else:
            system_text = system
        oai_messages.append({"role": "system", "content": system_text})

    for msg in body.get("messages", []):
        role = msg["role"]
        content = msg.get("content", "")

        if role == "assistant":
            if isinstance(content, list):
                text_parts = []
                thinking_parts = []
                tool_calls = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "thinking":
                            thinking_parts.append(block.get("thinking", ""))
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "index": len(tool_calls),
                                "id": block.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": json.dumps(block.get("input", {}))
                                }
                            })
                msg_content = "\n".join(text_parts) if text_parts else ""
                thinking_text = "\n".join(thinking_parts) if thinking_parts else ""
                if tool_calls:
                    ai_msg = {
                        "role": "assistant",
                        "content": msg_content or None,
                        "tool_calls": tool_calls
                    }
                    if thinking_text:
                        ai_msg["reasoning_content"] = thinking_text
                    oai_messages.append(ai_msg)
                else:
                    ai_msg = {"role": "assistant", "content": msg_content}
                    if thinking_text:
                        ai_msg["reasoning_content"] = thinking_text
                    oai_messages.append(ai_msg)
            else:
                oai_messages.append({"role": "assistant", "content": content})

        elif role == "user":
            if isinstance(content, list):
                # Check if this user message contains tool results
                tool_results = []
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_result":
                            tool_results.append({
                                "role": "tool",
                                "tool_call_id": block.get("tool_use_id", ""),
                                "name": block.get("name", ""),
                                "content": block.get("content", "")
                            })
                        elif block.get("type") == "text":
                            text_parts.append(block.get("text", ""))

                # If we have tool results, add them as tool messages (OpenAI format)
                # Only add a user message if there's actual text content
                if tool_results:
                    if text_parts:
                        oai_messages.append({"role": "user", "content": "\n".join(text_parts)})
                    oai_messages.extend(tool_results)
                else:
                    oai_messages.append({"role": "user", "content": "\n".join(text_parts)})
            else:
                oai_messages.append({"role": "user", "content": content})

    oai_request = {
        "model": body["model"],
        "messages": oai_messages,
        "max_tokens": body.get("max_tokens", 4096),
    }

    if "temperature" in body:
        oai_request["temperature"] = body["temperature"]
    if "top_p" in body:
        oai_request["top_p"] = body["top_p"]

    # Handle tools
    tools = body.get("tools")
    if tools:
        oai_tools = []
        for tool in tools:
            tool_type = tool.get("type", "")
            # Anthropic tool format: name, description, input_schema
            # Also handle special Anthropic tool types (text_editor, computer, etc.)
            if tool_type == "text_editor_20250124":
                oai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "str_replace_editor"),
                        "description": "Text editor tool for editing files",
                        "parameters": tool.get("input_schema", {"type": "object", "properties": {}})
                    }
                })
            elif tool_type == "computer_20241022":
                oai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "computer"),
                        "description": "Computer control tool",
                        "parameters": tool.get("input_schema", {"type": "object", "properties": {}})
                    }
                })
            else:
                oai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {"type": "object", "properties": {}})
                    }
                })
        oai_request["tools"] = oai_tools

    # Handle tool_choice
    tool_choice = body.get("tool_choice")
    if tool_choice:
        if isinstance(tool_choice, dict) and tool_choice.get("type") == "tool":
            oai_request["tool_choice"] = {
                "type": "function",
                "function": {"name": tool_choice.get("name", "")}
            }
        elif tool_choice == "auto":
            oai_request["tool_choice"] = "auto"
        elif tool_choice == "any":
            oai_request["tool_choice"] = "required"
        elif tool_choice == "none":
            oai_request["tool_choice"] = "none"

    # Handle stop_sequences
    stop = body.get("stop_sequences")
    if stop:
        oai_request["stop"] = stop

    # Handle thinking budget
    thinking = body.get("thinking")
    if thinking and thinking.get("type") == "enabled":
        budget = thinking.get("budget_tokens", 1024)
        if budget <= 1024:
            oai_request["reasoning_effort"] = "low"
        elif budget <= 2048:
            oai_request["reasoning_effort"] = "medium"
        else:
            oai_request["reasoning_effort"] = "high"

    return oai_request


def openai_response_to_anthropic(openai_resp: dict, model: str, stream: bool = False) -> dict:
    """Convert OpenAI Chat Completions response to Anthropic Messages format."""
    choice = openai_resp.get("choices", [{}])[0]
    message = choice.get("message", {})
    finish = choice.get("finish_reason", "stop")
    usage = openai_resp.get("usage", {})

    anthropic_content = []

    # Add reasoning content if present
    reasoning = message.get("reasoning_content") or openai_resp.get("reasoning_content")
    if reasoning:
        anthropic_content.append({
            "type": "thinking",
            "thinking": reasoning,
            "signature": openai_resp.get("id", "sig-0000")
        })

    # Handle tool calls
    tool_calls = message.get("tool_calls")
    if tool_calls:
        for tc in tool_calls:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                args = {}
            anthropic_content.append({
                "type": "tool_use",
                "id": tc.get("id", "tool_0"),
                "name": fn.get("name", ""),
                "input": args
            })
        stop_reason = "tool_use"
    elif message.get("content"):
        anthropic_content.append({
            "type": "text",
            "text": message["content"]
        })
        stop_reason = "end_turn" if finish in ("stop", "length") else "max_tokens"
    else:
        anthropic_content.append({
            "type": "text",
            "text": ""
        })
        stop_reason = "end_turn" if finish in ("stop", "length") else "max_tokens"

    return {
        "id": openai_resp.get("id", "msg_0000"),
        "type": "message",
        "role": "assistant",
        "content": anthropic_content,
        "model": openai_resp.get("model", model),
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "cache_creation_input_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) or 0,
            "cache_read_input_tokens": 0,
        }
    }


@app.post("/v1/messages")
async def v1_messages(request: Request):
    """Handle Anthropic Messages API requests."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model", "deepseek-v4-pro")
    stream = body.get("stream", False)

    # Translate
    oai_request = anthropic_messages_to_openai(body)

    print(f"[PROXY] model={model} stream={stream} messages={len(oai_request['messages'])} tools={'tools' in oai_request}")

    headers = {
        "Authorization": f"Bearer {OPENCODE_API_KEY}",
        "Content-Type": "application/json"
    }

    timeout = httpx.Timeout(120.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        if stream:
            return StreamingResponse(
                sse_generator(OPENCODE_BASE, headers, oai_request, model),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
        else:
            resp = await client.post(OPENCODE_BASE, headers=headers, json=oai_request)

            if resp.status_code != 200:
                print(f"[PROXY] Error {resp.status_code}: {resp.text[:500]}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Upstream error: {resp.text[:300]}"
                )

            openai_response = resp.json()
            anthropic_response = openai_response_to_anthropic(openai_response, model, False)
            return anthropic_response


async def sse_generator(url, headers, body, model):
    """Stream OpenAI response and translate to Anthropic SSE format."""
    oai_headers = {**headers}
    body["stream"] = True
    body["stream_options"] = {"include_usage": True}

    msg_id = None
    content_index = 0
    current_block_type = None
    current_tool_name = ""
    current_tool_id = ""
    has_started = False
    tool_calls_buffer = {}
    finish_reason = None
    usage_data = {}

    timeout = httpx.Timeout(120.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=oai_headers, json=body) as response:
            if response.status_code != 200:
                body_text = ""
                async for chunk in response.aiter_bytes():
                    body_text += chunk.decode(errors="ignore")
                yield f"event: error\ndata: {{\"error\":{{\"type\":\"upstream_error\",\"message\":\"HTTP {response.status_code}\"}}}}\n\n"
                return

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    if "usage" in chunk:
                        usage_data = chunk["usage"]
                    continue

                choice = choices[0]
                delta = choice.get("delta", {})
                r_finish = choice.get("finish_reason")
                if r_finish:
                    finish_reason = r_finish

                if not msg_id:
                    msg_id = chunk.get("id", "msg_stream")

                reasoning = delta.get("reasoning_content")
                if reasoning:
                    if not has_started:
                        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'model': model, 'content': [], 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
                        has_started = True

                    if current_block_type != "thinking":
                        current_block_type = "thinking"
                        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': content_index, 'content_block': {'type': 'thinking', 'thinking': ''}})}\n\n"

                    yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': content_index, 'delta': {'type': 'thinking_delta', 'thinking': reasoning}})}\n\n"
                    continue

                tool_calls = delta.get("tool_calls")
                if tool_calls:
                    if not has_started:
                        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'model': model, 'content': [], 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
                        has_started = True

                    for tc in tool_calls:
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"name": "", "arguments": "", "id": ""}
                        buf = tool_calls_buffer[idx]
                        if "id" in tc:
                            buf["id"] = tc["id"]
                        if "function" in tc:
                            fn = tc["function"]
                            if "name" in fn:
                                buf["name"] = fn["name"]
                            if "arguments" in fn:
                                buf["arguments"] += fn["arguments"]

                        if buf["name"] and not current_tool_id:
                            current_block_type = "tool_use"
                            current_tool_name = buf["name"]
                            current_tool_id = buf["id"] or "tool_" + str(content_index)
                            yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': content_index, 'content_block': {'type': 'tool_use', 'id': current_tool_id, 'name': current_tool_name, 'input': {}}})}\n\n"

                        if buf["name"]:
                            for idx_sorted in sorted(tool_calls_buffer.keys()):
                                b = tool_calls_buffer[idx_sorted]
                                if b["arguments"]:
                                    yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': content_index, 'delta': {'type': 'input_json_delta', 'partial_json': b['arguments']}})}\n\n"
                                    b["arguments"] = ""
                    continue

                text = delta.get("content")
                if text:
                    if not has_started:
                        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'model': model, 'content': [], 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
                        has_started = True

                    if current_block_type != "text":
                        if current_block_type:
                            yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': content_index})}\n\n"
                            content_index += 1
                        current_block_type = "text"
                        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': content_index, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

                    yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': content_index, 'delta': {'type': 'text_delta', 'text': text}})}\n\n"

    if current_block_type and has_started:
        yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': content_index})}\n\n"
        content_index += 1

    if has_started:
        anthropic_stop = "end_turn"
        if finish_reason == "tool_calls":
            anthropic_stop = "tool_use"
        elif finish_reason == "length":
            anthropic_stop = "max_tokens"
        elif finish_reason == "stop":
            anthropic_stop = "end_turn"

        yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': anthropic_stop, 'stop_sequence': None}, 'usage': {'output_tokens': usage_data.get('completion_tokens', 0)}})}\n\n"
        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/messages/count_tokens")
async def count_tokens(request: Request):
    """Simple token count endpoint. Claude Code uses this for context management."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    messages = body.get("messages", [])
    system = body.get("system", "")
    tools = body.get("tools", [])

    total = 0
    if system:
        if isinstance(system, str):
            total += len(system.split()) * 2
        elif isinstance(system, list):
            for s in system:
                total += len(s.get("text", "").split()) * 2

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += len(content.split()) * 2
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        total += len(block.get("text", "").split()) * 2
                    elif block.get("type") == "tool_use":
                        total += len(json.dumps(block.get("input", {}))) // 2
                    elif block.get("type") == "tool_result":
                        total += len(str(block.get("content", ""))) // 2

    for tool in tools:
        total += len(json.dumps(tool)) // 2

    return {"input_tokens": max(total, 1)}


@app.get("/v1/models")
async def list_models():
    """List available models. Claude Code uses this for model discovery.
    Configure via AVAILABLE_MODELS env var (comma-separated)."""
    models = []
    for name in AVAILABLE_MODELS.split(","):
        name = name.strip()
        if name:
            models.append({
                "id": name,
                "object": "model",
                "created": 1777847314,
                "owned_by": "opencode"
            })
    return {"object": "list", "data": models}


if __name__ == "__main__":
    import uvicorn
    print(f"[PROXY] Starting on {PROXY_HOST}:{PROXY_PORT}")
    print(f"[PROXY] Upstream: {OPENCODE_BASE}")
    print(f"[PROXY] Models: {AVAILABLE_MODELS}")
    uvicorn.run(app, host=PROXY_HOST, port=PROXY_PORT)
