"""Token-usage transcript parsing (parity with the TS SDK's token_usage.ts)."""

import json

from armoriq_sdk.token_usage import summarize_transcript_usage


def _write(tmp_path, lines):
    p = tmp_path / "transcript.jsonl"
    p.write_text("\n".join(json.dumps(o) for o in lines))
    return str(p)


def test_sums_anthropic_usage_by_model(tmp_path):
    path = _write(
        tmp_path,
        [
            {"message": {"model": "claude-opus-4-8", "usage": {"input_tokens": 10, "output_tokens": 5}}},
            {"message": {"model": "claude-opus-4-8", "usage": {"input_tokens": 3, "output_tokens": 2, "cache_read_input_tokens": 7}}},
            {"message": {"model": "<synthetic>", "usage": {"input_tokens": 99}}},
        ],
    )
    out = summarize_transcript_usage(path)
    assert len(out) == 1
    e = out[0]
    assert e["model"] == "claude-opus-4-8"
    assert e["inputTokens"] == 13 and e["outputTokens"] == 7 and e["cacheReadTokens"] == 7


def test_tolerates_openai_shape(tmp_path):
    path = _write(
        tmp_path,
        [{"model": "gpt-x", "usage": {"prompt_tokens": 4, "completion_tokens": 6,
                                       "prompt_tokens_details": {"cached_tokens": 2}}}],
    )
    out = summarize_transcript_usage(path)
    assert out[0]["inputTokens"] == 4 and out[0]["cacheReadTokens"] == 2


def test_returns_empty_on_bad_path():
    assert summarize_transcript_usage("/nonexistent/transcript.jsonl") == []
