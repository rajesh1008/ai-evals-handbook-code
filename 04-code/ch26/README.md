# Chapter 26 lab — Documents, Images and Voice Inputs

- `fixture.py` — 100 SIMULATED docs + 40 voice pilot turns (seed 2026).
- `lab.py` — five degradations + clean; layered e2e; WER vs task success.
- `inject.py` — transcription drops negative amounts (named d-300042).
- `try_its.py` — channel mix; clean vs glare; WER gate misses task fails.
- `real_vision.py` — modest REAL Anthropic labels on stub descriptions (`--live`).
- Truss 0.29 `multimodal`.

Run: `./run_all.sh` or `./run_all.sh --live`.
