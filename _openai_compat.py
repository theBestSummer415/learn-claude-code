"""
OpenAI compatibility shim — makes client.messages.create() look like Anthropic SDK.
Used by s02-s20 so only the import + client init line changes per file.
"""
import json
from types import SimpleNamespace
from openai import OpenAI as _OpenAI


# ── Block wrapper: gives .type / .name / .input / .id / .text ──────────────

class _Block(SimpleNamespace):
    """Mimics Anthropic content block interface."""
    pass


# ── Convert Anthropic tools → OpenAI tools ──────────────────────────────────

def _to_openai_tools(tools):
    if not tools:
        return None
    result = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        if "function" in t:
            result.append(t)          # already OpenAI format
        else:
            result.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            })
    return result or None


# ── Convert a stored content item → plain dict ──────────────────────────────

def _block_to_dict(item):
    if isinstance(item, dict):
        return item
    t = getattr(item, "type", None)
    if t == "text":
        return {"type": "text", "text": getattr(item, "text", "")}
    if t == "tool_use":
        inp = getattr(item, "input", {})
        return {"type": "tool_use", "id": item.id, "name": item.name, "input": inp}
    return {"type": "text", "text": str(item)}


# ── Convert Anthropic-format message history → OpenAI messages ──────────────

def _to_openai_messages(system, anthropic_messages):
    result = []
    if system:
        result.append({"role": "system", "content": system})

    for msg in anthropic_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "assistant":
            if isinstance(content, list):
                text_parts, tool_calls = [], []
                for item in content:
                    d = _block_to_dict(item)
                    if d.get("type") == "text":
                        text_parts.append(d.get("text", ""))
                    elif d.get("type") == "tool_use":
                        args = d.get("input", {})
                        if isinstance(args, dict):
                            args = json.dumps(args)
                        tool_calls.append({
                            "id": d["id"],
                            "type": "function",
                            "function": {"name": d["name"], "arguments": args},
                        })
                entry = {"role": "assistant", "content": "\n".join(text_parts) or None}
                if tool_calls:
                    entry["tool_calls"] = tool_calls
                result.append(entry)
            else:
                result.append({"role": "assistant", "content": str(content) if content else None})

        elif role == "user":
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "tool_result":
                            result.append({
                                "role": "tool",
                                "tool_call_id": item.get("tool_use_id", ""),
                                "content": str(item.get("content", "")),
                            })
                        elif item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        else:
                            text_parts.append(str(item))
                    else:
                        text_parts.append(str(item))
                if text_parts:
                    result.append({"role": "user", "content": "\n".join(text_parts)})
            else:
                result.append({"role": "user", "content": str(content)})

        else:
            result.append({"role": role, "content": str(content)})

    return result


# ── Response wrapper: response.content / response.stop_reason ───────────────

class _Response:
    def __init__(self, oai_response):
        choice = oai_response.choices[0]
        msg = choice.message
        finish = choice.finish_reason

        if finish == "tool_calls":
            self.stop_reason = "tool_use"
        elif finish == "length":
            self.stop_reason = "max_tokens"
        else:
            self.stop_reason = "end_turn"

        blocks = []
        if msg.content:
            blocks.append(_Block(type="text", text=msg.content))
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    inp = json.loads(tc.function.arguments or "{}")
                except Exception:
                    inp = {}
                blocks.append(_Block(
                    type="tool_use",
                    id=tc.id,
                    name=tc.function.name,
                    input=inp,
                ))
        self.content = blocks


# ── messages.create() — the shim ────────────────────────────────────────────

class _Messages:
    def __init__(self, oai_client):
        self._client = oai_client

    def create(self, model, messages, system="", tools=None, max_tokens=8000, **kwargs):
        oai_messages = _to_openai_messages(system, messages)
        oai_tools = _to_openai_tools(tools)

        kwargs_clean = {k: v for k, v in kwargs.items()
                        if k in ("temperature", "top_p", "stream")}

        response = self._client.chat.completions.create(
            model=model,
            messages=oai_messages,
            tools=oai_tools,
            max_tokens=max_tokens,
            **kwargs_clean,
        )
        return _Response(response)


# ── Drop-in Anthropic client ─────────────────────────────────────────────────

class Anthropic:
    """Drop-in replacement: Anthropic(api_key=..., base_url=...) → OpenAI under the hood."""

    def __init__(self, api_key=None, base_url=None, **kwargs):
        self.messages = _Messages(_OpenAI(api_key=api_key, base_url=base_url))
