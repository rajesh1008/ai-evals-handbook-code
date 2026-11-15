"""Plumbing test for the LOCAL-MODEL backend (no model, no key, no network beyond 127.0.0.1).

Starts mock_server.py, points LLM_BACKEND=local at it, runs the local path of chapters 5, 13, 14 and 15
in a scratch copy of 04-code, and checks that (1) the requests reach the server in OpenAI format,
(2) output is labelled LOCAL-MODEL, (3) everything lands under out/local/, and (4) no reference cache
or OUTPUT.txt changes. Run: python3 04-code/local_model/test_local_backend.py"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(CODE))
import mock_server  # noqa: E402


PREREQ = {("ch13", "lab.py"), ("ch13", "june_docs.py")}


def digest(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and "local" not in p.relative_to(root).parts and "__pycache__" not in p.parts:
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main():
    srv = mock_server.serve(0); threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/v1"
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env.update(LLM_BACKEND="local", LOCAL_LLM_BASE_URL=url, LOCAL_LLM_MODEL="mock-model")

    os.environ.update(LLM_BACKEND="local", LOCAL_LLM_BASE_URL=url, LOCAL_LLM_MODEL="mock-model")
    import llm_backend as LB
    r = LB.chat("hello", system="sys", max_tokens=5)
    assert r["text"] == mock_server.REPLY and r["model"] == "local:mock-model", r
    last = mock_server.CALLS[-1]
    assert last["model"] == "mock-model" and last["messages"][0] == {"role": "system", "content": "sys"}, last
    print("chat(): OK, OpenAI chat-completions request and response")

    tmp = Path(tempfile.mkdtemp(prefix="localtest-"))
    try:
        shutil.copytree(CODE, tmp / "04-code", ignore=shutil.ignore_patterns("__pycache__", "local", ".venv"))
        root = tmp / "04-code"
        before = digest(root)
        steps = [("ch05", ["python3", "model_coding.py"]),
                 ("ch13", ["python3", "probe.py"]),
                 ("ch13", ["python3", "lab.py"]),
                 ("ch13", ["python3", "june_docs.py"]),
                 ("ch13", ["python3", "june_run.py"]),
                 ("ch14", ["python3", "prelabel.py"]),
                 ("ch14", ["python3", "lab.py"]),
                 ("ch14", ["python3", "try_its.py", "3"]),
                 ("ch15", ["python3", "probe.py"]),
                 ("ch15", ["python3", "lab.py"]),
                 ("ch15", ["python3", "try_its.py"])]
        for ch, cmd in steps:
            n0 = len(mock_server.CALLS)
            if ch == "ch05" and not (root / "ch05/out/lab.json").exists():
                subprocess.run(["python3", "lab.py"], cwd=root / ch, env=env, check=True, capture_output=True)
                before = digest(root)
            p = subprocess.run(cmd, cwd=root / ch, env={**env, "PYTHONPATH": str(root / "truss")},
                               capture_output=True, text=True, timeout=900)
            assert p.returncode == 0, (ch, p.stdout[-800:], p.stderr[-1500:])
            if (ch, cmd[1]) in PREREQ:   # SIMULATED fixtures other steps read; no model involved
                before = digest(root); continue
            assert "LOCAL-MODEL" in p.stdout, (ch, p.stdout[:400])
            made = sorted(str(x.relative_to(root / ch)) for x in (root / ch / "out" / "local").rglob("*") if x.is_file())
            assert made, ch
            print(f"{ch} {' '.join(cmd[1:])}: OK, {len(mock_server.CALLS) - n0} calls, wrote {made[:4]}{' ...' if len(made) > 4 else ''}")
        after = digest(root)
        changed = [k for k in before if before[k] != after.get(k)]
        assert not changed, f"reference files changed: {changed}"
        print(f"reference files unchanged: {len(before)} checked (OUTPUT.txt and every cached reply outside out/local/)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True); srv.shutdown()
    print("PASS")


if __name__ == "__main__":
    main()
