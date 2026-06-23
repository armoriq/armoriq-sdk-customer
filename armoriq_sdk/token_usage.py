"""Token-usage capture — shared across all ArmorIQ tool integrations.

Mirrors the TypeScript SDK's token_usage.ts. ``record_token_usage`` on the
client is the single transport every tool posts through; ``summarize_transcript_usage``
parses an Anthropic/OpenAI-style JSONL transcript into per-model entries.
"""

import json
from typing import Any, Dict, List, Optional


def _first(usage: Dict[str, Any], *keys: str) -> Optional[Any]:
    """First present (non-None) value among keys — matches TS `??` semantics."""
    for k in keys:
        v = usage.get(k)
        if v is not None:
            return v
    return None


def summarize_transcript_usage(transcript_path: str) -> List[Dict[str, Any]]:
    """Parse a JSONL transcript and sum LLM token usage by model. Tolerates
    Anthropic (Claude Code) and OpenAI (Codex CLI) shapes. Pure + defensive:
    returns [] on any read/parse error; skips synthetic and zero-usage lines.
    """
    try:
        with open(transcript_path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        return []

    by_model: Dict[str, Dict[str, Any]] = {}
    for line in raw.split("\n"):
        trimmed = line.strip()
        if not trimmed:
            continue
        try:
            obj = json.loads(trimmed)
        except (ValueError, TypeError):
            continue
        if not isinstance(obj, dict):
            continue

        msg = obj.get("message") or obj.get("payload") or obj
        usage = (msg.get("usage") if isinstance(msg, dict) else None) or obj.get("usage")
        model = ""
        if isinstance(msg, dict) and isinstance(msg.get("model"), str):
            model = msg["model"]
        elif isinstance(obj.get("model"), str):
            model = obj["model"]
        if not usage or not isinstance(usage, dict) or not model or model == "<synthetic>":
            continue

        in_tok = int(_first(usage, "input_tokens", "prompt_tokens") or 0)
        out_tok = int(_first(usage, "output_tokens", "completion_tokens") or 0)
        details = usage.get("prompt_tokens_details")
        cached = details.get("cached_tokens") if isinstance(details, dict) else None
        cache_read = int(_first(usage, "cache_read_input_tokens") or cached or 0)
        cache_write = int(usage.get("cache_creation_input_tokens") or 0)
        if in_tok + out_tok + cache_read + cache_write == 0:
            continue

        acc = by_model.setdefault(
            model,
            {
                "model": model,
                "inputTokens": 0,
                "outputTokens": 0,
                "cacheReadTokens": 0,
                "cacheWriteTokens": 0,
            },
        )
        acc["inputTokens"] += in_tok
        acc["outputTokens"] += out_tok
        acc["cacheReadTokens"] += cache_read
        acc["cacheWriteTokens"] += cache_write

    return list(by_model.values())
