"""Chapter 26 manuscript structural assertions."""
from __future__ import annotations
import re, hashlib, subprocess
from pathlib import Path

ROOT = Path("/workspace/ai-evals-book")
import pytest
if not (ROOT / "02-manuscript").is_dir():
    pytest.skip("needs the book's manuscript sources, which are not part of the companion code", allow_module_level=True)
MD = (ROOT / "02-manuscript/ch26.md").read_text()


def test_build_stable_fr_after_iv():
    h1 = hashlib.sha256((ROOT / "02-manuscript/ch26.md").read_bytes()).hexdigest()
    subprocess.check_call(["bash", str(ROOT / "02-manuscript/ch26-parts/build.sh")])
    h2 = hashlib.sha256((ROOT / "02-manuscript/ch26.md").read_bytes()).hexdigest()
    assert h1 == h2
    assert MD.find("## Further reading") > MD.find("## Interview Questions and Answers") > 0


def test_figures_1_to_12_embedded_ordered():
    body = MD.split("## Interview Questions and Answers")[0]
    first = []
    for m in re.finditer(r"(?:fig26-(\d+)|Figure 26\.(\d+))", body):
        n = m.group(1) or m.group(2)
        if n not in first:
            first.append(n)
    embeds = re.findall(r"(?m)^!\[.*?\]\([^)]*fig26-(\d+)", body)
    assert first == [str(i) for i in range(1, 13)]
    assert embeds == [str(i) for i in range(1, 13)]


def test_h2_depth_footnotes_interview():
    body = MD.split("## Interview Questions and Answers")[0]
    assert len(re.findall(r"(?m)^## ", body)) <= 16
    assert MD.count("### Depth (a–f)") >= 6
    pre, fr = MD.split("## Further reading", 1)
    for n in range(1, 8):
        assert f"[^{n}]" in pre
        assert f"[^{n}]:" in fr
    iv = MD[MD.find("## Interview Questions and Answers"): MD.find("## Further reading")]
    blocks = re.split(r"(?m)^(\*\*\d+\.\s+[^*]+\*\*)\s*", iv)
    assert (len(blocks) - 1) // 2 == 14
    for i in range(1, len(blocks), 2):
        bolds = re.findall(r"\*\*([^*]+)\*\*", blocks[i + 1])
        assert len(bolds) == 1 and len(bolds[0].split()) >= 6
        assert 150 <= len(blocks[i + 1].split()) <= 450
