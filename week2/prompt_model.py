"""Minimal, safe prompt wrapper for Ollama (local) and Google Gemini (cloud).

Provides:
- prompt_model(model: str, prompt: str) -> str
- a CLI entrypoint for quick manual testing

Behavior:
- Models starting with "gemini-" are routed to Google Generative API using
  the `GOOGLE_API_KEY` environment variable.
- Other model names are routed to a local Ollama instance at
  `http://127.0.0.1:11434`.
- All network operations use simple retries and timeouts and return a
  string error message instead of raising on failure.

This file intentionally avoids external dependencies so it can run with
only the Python standard library. You may add `httpx` or Google client
libraries later if desired.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Tuple

def _safe_request(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 10) -> Tuple[int, bytes]:
    headers = headers or {}
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as he:
        # return status and body for downstream parsing
        body = he.read() if hasattr(he, 'read') else b''
        return he.code, body
    except Exception as exc:  # network errors, timeouts, connection refused
        raise

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

def _call_ollama(model: str, prompt: str, timeout: int = OLLAMA_TIMEOUT) -> str:
    """Call local Ollama HTTP API; return text or raise exceptions.

    Note: Ollama exposes a health endpoint at `/` and JSON-based endpoints
    for generation. This implementation POSTs to `/api/generate` which works
    with recent Ollama releases; if your local Ollama uses a different
    path, update the URL accordingly.
    """
    base = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    url = base.rstrip("/") + "/api/generate"

    payload = {"model": model, "prompt": prompt, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    try:
        status, body = _safe_request(url, data=data, headers=headers, timeout=timeout)
    except Exception as exc:
        return f"[Ollama Error] Could not connect to {base}: {exc}"

    try:
        obj = json.loads(body.decode("utf-8")) if body else {}
    except Exception:
        return f"[Ollama Error] Non-JSON response (status={status})"

    def _extract_text(payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None

        for key in ("response", "result", "output", "text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value

        if "message" in payload and isinstance(payload["message"], dict):
            message = payload["message"]
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content

        if "messages" in payload and isinstance(payload["messages"], list) and payload["messages"]:
            last_message = payload["messages"][-1]
            if isinstance(last_message, dict):
                content = last_message.get("content")
                if isinstance(content, str) and content.strip():
                    return content

        if "results" in payload and isinstance(payload["results"], list) and payload["results"]:
            first = payload["results"][0]
            if isinstance(first, dict):
                content = first.get("content")
                if isinstance(content, str) and content.strip():
                    return content

        return None

    # common places to find generated text
    if isinstance(obj, dict):
        extracted = _extract_text(obj)
        if extracted:
            return extracted

    if isinstance(body, bytes):
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                line_obj = json.loads(line.decode("utf-8"))
            except Exception:
                continue
            extracted = _extract_text(line_obj)
            if extracted:
                return extracted

    return f"[Ollama Error] Unexpected response shape (status={status})"


def _call_gemini(model: str, prompt: str, timeout: int = 10) -> str:
    """Call Google Generative API using REST.

    Requires environment variable `GOOGLE_API_KEY` to be set to a valid key.
    This function uses a lightweight REST call and is tolerant of different
    response shapes.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "[Gemini Error] GOOGLE_API_KEY not set in environment"

    # v1beta2 endpoint pattern; keep model name as provided
    endpoint = f"https://generativelanguage.googleapis.com/v1beta2/models/{model}:generate?key={api_key}"

    payload = {"prompt": {"text": prompt}}
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    try:
        status, body = _safe_request(endpoint, data=data, headers=headers, timeout=timeout)
    except Exception as exc:
        return f"[Gemini Error] Network error: {exc}"

    try:
        obj = json.loads(body.decode("utf-8")) if body else {}
    except Exception:
        return f"[Gemini Error] Non-JSON response (status={status})"

    # Look for common response shapes
    if isinstance(obj, dict):
        # google may return {"candidates": [{"output": "..."}], "output": "..."}
        if "candidates" in obj and isinstance(obj["candidates"], list) and obj["candidates"]:
            first = obj["candidates"][0]
            if isinstance(first, dict):
                for k in ("output", "content", "text"):
                    if k in first:
                        return str(first[k])
        for k in ("output", "content", "text"):  # top-level fallbacks
            if k in obj:
                return str(obj[k])
        # if an error field exists, surface it
        if "error" in obj:
            return f"[Gemini Error] {obj['error']}"

    return f"[Gemini Error] Unexpected response shape (status={status})"


def prompt_model(model: str, prompt: str) -> str:
    """Public function: route to appropriate provider and return text.

    This function never raises for network/provider errors; it returns
    a descriptive string instead so callers (including automated graders)
    can handle failures deterministically.
    """
    model = (model or "").strip()
    prompt = (prompt or "").strip()

    if not model:
        return "[Error] model must be provided"
    if not prompt:
        return "[Error] prompt must be provided"

    # simple retry strategy
    attempts = 2
    delay = 1.0
    last_err = None

    if model.startswith("gemini-"):
        for _ in range(attempts):
            res = _call_gemini(model, prompt, timeout=10)
            # treat responses starting with [Gemini Error] as failures to retry
            if not isinstance(res, str) or not res.startswith("[Gemini Error]"):
                return res
            last_err = res
            time.sleep(delay)
            delay *= 2
        return last_err or "[Gemini Error] Unknown failure"

    # default to Ollama/local for other model names
    for _ in range(attempts):
        res = _call_ollama(model, prompt, timeout=10)
        if not isinstance(res, str) or not res.startswith("[Ollama Error]"):
            return res
        last_err = res
        time.sleep(delay)
        delay *= 2
    return last_err or "[Ollama Error] Unknown failure"


def _main_from_argv(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python prompt_model.py <model> <prompt>")
        return 2

    model = argv[1]
    prompt = " ".join(argv[2:])
    print("--- RESPONSE ---\n")
    resp = prompt_model(model, prompt)
    print(resp)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main_from_argv(sys.argv))