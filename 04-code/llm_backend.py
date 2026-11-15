"""Shared switches for the labs' model-calling paths.

Three ways a lab that uses model replies can run:

1. Offline (default). Cached REAL replies in out/ are replayed; no API is called and no key is needed.
   If a chapter's cache is missing from out/ (for example after you delete it to rerun) the step prints a
   SKIP line that points to OUTPUT.txt, which holds the recorded run the book quotes.
2. Live Anthropic (paid, explicit). Only when you pass `run` or `--live` (or set LABS_LIVE=1) and
   ANTHROPIC_API_KEY is in the environment. Nothing in the labs falls back to a paid call on its own.
3. Local model (free, explicit). Any OpenAI-compatible chat-completions server, for example Ollama,
   llama.cpp's llama-server, vLLM or LM Studio:

       export LLM_BACKEND=local
       export LOCAL_LLM_BASE_URL=http://localhost:11434/v1   # Ollama; llama-server uses http://localhost:8080/v1
       export LOCAL_LLM_MODEL=qwen2.5:0.5b                    # any model name the server knows
       export LOCAL_LLM_API_KEY=...                           # optional, sent as a Bearer token
       export LOCAL_LLM_MAX_TOKENS=400                        # optional cap on reply length (slow CPUs)
       export LOCAL_LLM_TIMEOUT=1800                          # optional seconds per request (default 600)

   then pass `run` (or `--live`) as for a live run. Replies and summaries are written under out/local/,
   never over the cached reference files, and every printed block is labelled LOCAL-MODEL. A local
   model's numbers will differ from the book's; they are not a reproduction of it.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

LABEL = "LOCAL-MODEL"


def is_local() -> bool:
    return os.environ.get("LLM_BACKEND", "").strip().lower() == "local"


def live_requested(argv) -> bool:
    return any(a in ("run", "--live") for a in argv[1:]) or os.environ.get("LABS_LIVE") == "1"


def base_url() -> str:
    return os.environ.get("LOCAL_LLM_BASE_URL", "").rstrip("/")


def model() -> str:
    return os.environ.get("LOCAL_LLM_MODEL", "")


def require_local() -> None:
    missing = [k for k in ("LOCAL_LLM_BASE_URL", "LOCAL_LLM_MODEL") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"LLM_BACKEND=local needs {' and '.join(missing)} (see 04-code/LOCAL_MODEL.md)")


def local_path(chapter_dir, *parts) -> Path:
    """Where a local-model run writes: <chapter>/out/local/<parts>. Never a reference cache."""
    p = Path(chapter_dir).resolve() / "out" / "local" / Path(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def pick(chapter_dir, reference: Path, *local_parts) -> Path:
    """The reference cache path offline or live, the out/local/ path under LLM_BACKEND=local."""
    return local_path(chapter_dir, *(local_parts or (Path(reference).name,))) if is_local() else Path(reference)


def chat(prompt: str, system: str | None = None, max_tokens: int = 512, temperature: float = 0.0,
         timeout: float = 600.0) -> dict:
    """One chat-completions call to the local server. Returns text, token counts and the model name."""
    require_local()
    if os.environ.get("LOCAL_LLM_MAX_TOKENS"):
        max_tokens = min(max_tokens, int(os.environ["LOCAL_LLM_MAX_TOKENS"]))
    timeout = float(os.environ.get("LOCAL_LLM_TIMEOUT") or timeout)
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = json.dumps({"model": model(), "messages": msgs, "max_tokens": max_tokens,
                       "temperature": temperature, "stream": False}).encode()
    headers = {"content-type": "application/json"}
    if os.environ.get("LOCAL_LLM_API_KEY"):
        headers["authorization"] = "Bearer " + os.environ["LOCAL_LLM_API_KEY"]
    req = urllib.request.Request(base_url() + "/chat/completions", data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    usage = data.get("usage") or {}
    return {"text": (data["choices"][0]["message"].get("content") or ""),
            "in_tok": int(usage.get("prompt_tokens") or 0), "out_tok": int(usage.get("completion_tokens") or 0),
            "model": f"local:{data.get('model') or model()}"}


def banner(what: str) -> None:
    print(f"[{LABEL} RUN: {what}; model {model()} at {base_url()}. These numbers come from a local model and "
          f"will differ from the book; the cached reference replies in out/ are not read or changed.]")


def skip(what: str, cache: str, rerun: str) -> None:
    print(f"SKIP: {what} needs the cached REAL replies in {cache}, which are missing "
          f"from out/. The recorded run the book quotes is in this chapter's OUTPUT.txt. "
          f"To rerun this step: `{rerun}` with ANTHROPIC_API_KEY set (paid), or the same command with "
          f"LLM_BACKEND=local and a local model (see 04-code/LOCAL_MODEL.md); either way the numbers will "
          f"not be the book's.")
