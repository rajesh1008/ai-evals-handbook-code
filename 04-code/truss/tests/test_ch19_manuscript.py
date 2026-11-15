"""Chapter 19 manuscript structural assertions (figure order + interview)."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path("/workspace/ai-evals-book")
import pytest
if not (ROOT / "02-manuscript").is_dir():
    pytest.skip("needs the book's manuscript sources, which are not part of the companion code", allow_module_level=True)
MD = (ROOT / "02-manuscript/ch19.md").read_text()
IV = (ROOT / "02-manuscript/ch19-parts/p06-interview.md").read_text()


def test_build_stable_and_fr_after_interview():
    import subprocess, hashlib
    h1 = hashlib.sha256((ROOT / "02-manuscript/ch19.md").read_bytes()).hexdigest()
    subprocess.check_call(["bash", str(ROOT / "02-manuscript/ch19-parts/build.sh")])
    h2 = hashlib.sha256((ROOT / "02-manuscript/ch19.md").read_bytes()).hexdigest()
    assert h1 == h2
    iv = MD.find("## Interview Questions and Answers")
    fr = MD.find("## Further reading")
    assert iv > 0 and fr > iv


def test_figures_1_to_11_first_seen_and_embeds():
    body = MD.split("## Interview Questions and Answers")[0]
    first = []
    for m in re.finditer(r"(?:fig19-(\d+)|Figure 19\.(\d+))", body):
        n = m.group(1) or m.group(2)
        if n not in first:
            first.append(n)
    embeds = re.findall(r"(?m)^!\[.*?\]\([^)]*fig19-(\d+)", body)
    assert first == [str(i) for i in range(1, 12)]
    assert embeds == [str(i) for i in range(1, 12)]


def test_fourteen_answers_one_insight_bold():
    blocks = re.split(r"(?m)^(\*\*\d+\.\s+[^*]+\*\*)\s*", IV)
    assert (len(blocks) - 1) // 2 == 14
    for i in range(1, len(blocks), 2):
        body = blocks[i + 1]
        bolds = re.findall(r"\*\*([^*]+)\*\*", body)
        assert len(bolds) == 1
        assert len(bolds[0].split()) >= 6
        assert 150 <= len(body.split()) <= 450


def test_depth_a_f_blocks_for_five_methods():
    body = MD.split("## Interview Questions and Answers")[0]
    assert body.count("### Depth (a–f)") >= 5
    for letter in ["**(a)", "**(b)", "**(c)", "**(d)", "**(e)", "**(f)"]:
        assert letter in body
    # numbered procedures present
    assert "(1)" in body and "(5)" in body
