"""NEXUS Frontier Scanner — single-call validation probe.

Latency profile (validated 2026-07-03):
- NIM MiniMax-M3: first call ~38s, subsequent 60s+ (KV warm-up + 8 RPM cap)
- NIM GLM-5.2 / Qwen3-Next: 1.5-3s steady
- LongCat-2.0: 1-3s (cold-start rare, needs max_tokens>=1500)
- InternAI/Ollama/Mistral/Groq/Codestral/GitHub: 1-4s steady

Heavy-mode probes intentionally test the path-under-load (600 tokens); light-mode
only gates survival.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path


VALIDATION_TIMEOUT = 22   # light probe: sufficient for steady-state APIs
HEAVY_PROBE_TIMEOUT = 95  # heavy probe: MiniMax-M3 reasoning can reach 90s+
PROBE_TOKENS = 24
HEAVY_PROBE_TOKENS = 600
NIM_HEAVY_COOLDOWN = 70   # seconds — NIM 8 RPM cadence requires ~75s between heavy on same key


@dataclass
class ValidationResult:
    provider: str
    model_id: str
    decision: str
    status_code: int | None = None
    latency_ms: int = 0
    artifacts_path: str = ""
    response_excerpt: str = ""
    error: str | None = None
    finished_at: float = 0.0

    def to_json(self) -> dict:
        return asdict(self)


CHAT_ENDPOINTS = {
    "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
    "ollama-cloud": "https://ollama.com/v1/chat/completions",
    "longcat": "https://api.longcat.chat/openai/v1/chat/completions",
    "internai": "https://chat.intern-ai.org.cn/api/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "codestral": "https://codestral.mistral.ai/v1/chat/completions",
    "github": "https://models.inference.ai.azure.com/chat/completions",
}


AUTH_ENV = {
    "nvidia": "NVIDIA_API_KEY",
    "ollama-cloud": "OLLAMA_CLOUD_API_KEY",
    "longcat": "LONGCAT_API_KEY",
    "internai": "INTERN_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
    "codestral": "CODESTRAL_API_KEY",
    "github": "GITHUB_API_KEY",
}


VALIDATION_PROMPT = (
    "Reply with the single word: CONFIRMED. Do not output anything else."
)


def _key_for(provider: str) -> str:
    return os.environ.get(AUTH_ENV.get(provider, ""), "").strip()


def probe_model(provider: str, model_id: str, mode: str = "light") -> ValidationResult:
    endpoint = CHAT_ENDPOINTS.get(provider)
    result = ValidationResult(
        provider=provider,
        model_id=model_id,
        decision="unknown",
        finished_at=time.time(),
    )
    if not endpoint:
        result.decision = "no_endpoint"
        result.error = "Endpoint not configured"
        return result
    key = _key_for(provider)
    if mode == "heavy":
        timeout = HEAVY_PROBE_TIMEOUT
        max_tok = HEAVY_PROBE_TOKENS
        prompt = (
            "Reason step-by-step: When a frontier model receives a partner-level "
            "allocated quota with a 30-day rolling expiry, what three signals should "
            "a scheduler monitor to decide rate limits?"
        )
    else:
        timeout = VALIDATION_TIMEOUT
        max_tok = PROBE_TOKENS
        prompt = VALIDATION_PROMPT
    body = json.dumps(
        {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tok,
            "temperature": 0.0,
        }
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "NEXUS-FrontierScanner/0.1",
    }
    if key:
        headers["Authorization"] = "Bearer " + key

    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            result.status_code = getattr(resp, "status", 200)
            text = ""
            try:
                text = payload["choices"][0]["message"].get("content", "") or ""
            except (KeyError, IndexError, TypeError):
                text = ""
            result.response_excerpt = text[:200]
            result.latency_ms = int((time.time() - started) * 1000)
            if any(tok in text.upper() for tok in ("CONFIRMED", "TRUE", "OK")):
                result.decision = "pass"
            elif len(text.strip()) >= 2:
                result.decision = "pass_unfamiliar_reply"
            else:
                result.decision = "pass_empty"
    except urllib.error.HTTPError as e:
        result.status_code = e.code
        result.error = e.read().decode("utf-8", errors="replace")[:200]
        result.decision = "dead" if e.code in (404, 410) else f"http_{e.code}"
        result.latency_ms = int((time.time() - started) * 1000)
    except urllib.error.URLError as e:
        result.error = "url_" + str(e.reason)[:120]
        result.decision = "url_error"
        result.latency_ms = int((time.time() - started) * 1000)
    except (TimeoutError, json.JSONDecodeError) as e:
        result.error = str(e)[:120]
        result.decision = "timeout" if isinstance(e, TimeoutError) else "decode_error"
        result.latency_ms = int((time.time() - started) * 1000)
    return result


def save_result(result: ValidationResult, state_dir: Path) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    fname = f"probe__{result.provider}__{result.model_id.replace('/', '__')}.json"
    target = state_dir / fname
    target.write_text(
        json.dumps(result.to_json(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    result.artifacts_path = str(target)
    return target


def run_probe(provider: str, model_id: str, state_dir: Path, mode: str = "light") -> ValidationResult:
    res = probe_model(provider, model_id, mode=mode)
    save_result(res, state_dir)
    return res


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="One-shot validation probe.")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--mode", choices=("light", "heavy"), default="light")
    args = parser.parse_args()

    res = run_probe(args.provider, args.model, Path(args.state_dir), mode=args.mode)
    print(json.dumps(res.to_json(), indent=2, sort_keys=True))
