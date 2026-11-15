# Running the model steps on a local model

The labs replay cached REAL model replies by default and never call a model on their own. For the
chapters whose model step you may want to rerun without an Anthropic key, there is an optional local
backend: any server that speaks the OpenAI chat-completions API, such as
[Ollama](https://ollama.com), llama.cpp's `llama-server`, vLLM or LM Studio.

**A local model's numbers are not the book's numbers.** Every block such a run prints is labelled
`LOCAL-MODEL`, and its replies and summaries are written under the chapter's `out/local/` folder
(ignored by git). The cached reference replies and `OUTPUT.txt` are not read or changed.

## Chapters with a local backend

| Chapter | Step | Local output |
|---|---|---|
| 5 | `model_coding.py`: open grouping and closed coding of the 53 failing notes | `ch05/out/local/model/`, `ch05/out/local/OUTPUT.local.txt` |
| 13 | `june_run.py` (June document extraction) and `probe.py` (guideline ambiguity probe) | `ch13/out/local/` |
| 14 | `prelabel.py` (pre-labeller), the selection study and automation bias in `lab.py`, Try it 2 and 3 | `ch14/out/local/`, `ch14/out/local/OUTPUT.local.txt` |
| 15 | `probe.py` (decision-step probe), the two-way gate in `lab.py`, Try it 2 | `ch15/out/local/` |

The REAL replies of Chapters 13, 14 and 15 were re-recorded on 15 November 2026 and are cached in each
chapter's `out/`; a local run writes only under `out/local/` and leaves them and `OUTPUT.txt` alone. The other scripts that take a `run` or `--live` argument keep their
Anthropic-only live path.

## Setup

```bash
# Ollama
ollama pull qwen2.5:0.5b
export LLM_BACKEND=local
export LOCAL_LLM_BASE_URL=http://localhost:11434/v1
export LOCAL_LLM_MODEL=qwen2.5:0.5b

# or llama.cpp
llama-server -m qwen2.5-0.5b-instruct-q4_k_m.gguf --port 8080
export LLM_BACKEND=local LOCAL_LLM_BASE_URL=http://localhost:8080/v1 LOCAL_LLM_MODEL=qwen2.5-0.5b-instruct

# optional
export LOCAL_LLM_API_KEY=...        # sent as a Bearer token if your server wants one
export LOCAL_LLM_MAX_TOKENS=400     # cap reply length on a slow CPU
export LOCAL_LLM_TIMEOUT=1800       # seconds per request (default 600)
```

Then run the chapter as usual, for example `cd 04-code/ch15 && ./run_all.sh run` (with
`LLM_BACKEND=local` the scripts call the local server for any reply not yet cached under `out/local/`;
delete `out/local/` to start again). Unset `LLM_BACKEND` to go back to the cached reference run.

A live Anthropic run (paid) still needs both an explicit `run` or `--live` argument and
`ANTHROPIC_API_KEY` in your environment; nothing falls back to it automatically.

## Testing the plumbing without a model

`local_model/mock_server.py` is a tiny OpenAI-compatible server that returns one fixed placeholder
reply (it is not a model). `local_model/test_local_backend.py` starts it, runs the local path of
Chapters 5, 13, 14 and 15 in a scratch copy of `04-code`, and checks that the requests arrive in
OpenAI format, that the output is labelled `LOCAL-MODEL`, that everything lands under `out/local/`,
and that no reference file changes:

```bash
python3 04-code/local_model/test_local_backend.py
```
