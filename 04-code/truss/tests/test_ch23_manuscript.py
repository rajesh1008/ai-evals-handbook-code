"""Chapter 23 manuscript structural assertions (figures, IV bolds, FR footnotes)."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path("/workspace/ai-evals-book")
import pytest
if not (ROOT / "02-manuscript").is_dir():
    pytest.skip("needs the book's manuscript sources, which are not part of the companion code", allow_module_level=True)
MD = (ROOT / "02-manuscript/ch23.md").read_text()
IV = (ROOT / "02-manuscript/ch23-parts/p_interview.md").read_text()
FR = (ROOT / "02-manuscript/ch23-parts/p_further.md").read_text()
BODY = (ROOT / "02-manuscript/ch23-parts/p_body.md").read_text()


def test_build_stable_and_fr_after_interview():
    import subprocess, hashlib
    h1 = hashlib.sha256((ROOT / "02-manuscript/ch23.md").read_bytes()).hexdigest()
    subprocess.check_call(["bash", str(ROOT / "02-manuscript/ch23-parts/build.sh")])
    h2 = hashlib.sha256((ROOT / "02-manuscript/ch23.md").read_bytes()).hexdigest()
    assert h1 == h2
    iv = MD.find("## Interview Questions and Answers")
    fr = MD.find("## Further reading")
    assert iv > 0 and fr > iv
    assert FR.lstrip().startswith("## Further reading")


def test_figures_1_to_14_first_seen_and_embeds():
    body = MD.split("## Interview Questions and Answers")[0]
    first = []
    for m in re.finditer(r"(?:fig23-(\d+)|Figure 23\.(\d+))", body):
        n = m.group(1) or m.group(2)
        if n not in first:
            first.append(n)
    embeds = re.findall(r"(?m)^!\[.*?\]\([^)]*fig23-(\d+)", body)
    assert first == [str(i) for i in range(1, 15)]
    assert embeds == [str(i) for i in range(1, 15)]


def test_sixteen_answers_one_insight_bold():
    blocks = re.split(r"(?m)^(\*\*\d+\.\s+[^*]+\*\*)\s*", IV)
    assert (len(blocks) - 1) // 2 == 16
    for i in range(1, len(blocks), 2):
        body = blocks[i + 1]
        bolds = re.findall(r"\*\*([^*]+)\*\*", body)
        assert len(bolds) == 1, blocks[i]
        assert len(bolds[0].split()) >= 6, bolds[0]
        assert 150 <= len(body.split()) <= 450


def test_sequential_footnotes_wired():
    pre = MD.split("## Further reading")[0]
    for n in range(1, 10):
        assert f"[^{n}]" in pre
        assert f"[^{n}]:" in FR
