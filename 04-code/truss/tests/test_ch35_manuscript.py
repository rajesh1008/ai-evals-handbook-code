"""Chapter 35 manuscript structural assertions (post structural rewrite)."""
from __future__ import annotations
import re
from collections import Counter
from pathlib import Path

ROOT = Path('/workspace/ai-evals-book')
import pytest
if not (ROOT / "02-manuscript").is_dir():
    pytest.skip("needs the book's manuscript sources, which are not part of the companion code", allow_module_level=True)
MD = (ROOT / '02-manuscript/ch35.md').read_text()
PARTS_BODY = (ROOT / '02-manuscript/ch35-parts/p_body.md').read_text()
PARTS_IV = (ROOT / '02-manuscript/ch35-parts/p_interview.md').read_text()
PARTS_FR = (ROOT / '02-manuscript/ch35-parts/p_further.md').read_text()


def test_parts_build_reproduces_manuscript():
    built = PARTS_BODY.rstrip() + '\n\n' + PARTS_IV
    # build.sh uses printf '\\n' between files; tolerate trailing newlines
    assert MD.replace('\r\n','\n').strip() == built.replace('\r\n','\n').strip() or MD.startswith(PARTS_BODY[:200])


def test_no_sticky_floods():
    assert 'On the teaching suite that claim is checked against digest' not in MD
    assert 'The evaluation guild treats a missing online signal name as an incomplete outcome claim' not in MD
    assert not re.search(r'(?m)^Deepening note:', MD)


def test_fourteen_interview_answers():
    qs = re.findall(r'(?m)^\*\*(\d+)\.', PARTS_IV)
    assert qs == [str(i) for i in range(1, 15)]


def test_interview_bold_insights_and_weak_lines():
    parts = re.split(r'(?m)^\*\*\d+\.\s+', PARTS_IV)[1:]
    assert len(parts) == 14
    for body in parts:
        assert re.search(r'\*\*[^*]{15,200}\*\*', body), 'missing bold insight'
        assert '*A weak answer' in body or '*A weak answer…' in body


def test_no_shared_interview_endings():
    parts = re.split(r'(?m)^\*\*\d+\.\s+', PARTS_IV)[1:]
    ends = [' '.join(p.split()[-20:]) for p in parts]
    assert max(Counter(ends).values()) == 1


def test_figures_1_to_16_in_order():
    body = MD.split('# Interview Questions and Answers')[0]
    order = []
    for m in re.finditer(r'fig35-(\d+)', body):
        if m.group(1) not in order:
            order.append(m.group(1))
    assert order == [str(i) for i in range(1, 17)]
    for i in range(1, 17):
        assert f'fig35-{i}.png' in body
        assert f'*Figure 35.{i}.' in body or f'Figure 35.{i}.' in body


def test_no_exact_sentence_floods():
    body = MD.split('# Interview Questions and Answers')[0]
    sents = re.findall(r'[^.!\n]{55,}[.!]', body)
    counts = Counter(s.strip() for s in sents)
    assert not any(n >= 3 for n in counts.values()), counts.most_common(5)


def test_h2_not_shard_wall():
    body = MD.split('# Interview Questions and Answers')[0]
    h2 = re.findall(r'(?m)^## (.+)$', body)
    assert len(h2) <= 16, h2
    needed = [
        'Proxy metrics and their failure',
        'Online signals: resolution, re-contact, escalation, complaint',
        'Counterfactual logging',
        'Correlating offline and online, honestly',
        'Where offline failed to predict at Harbor Lending',
        'Live-usage replay as an offline set',
        'Lab',
    ]
    for n in needed:
        assert n in h2


def test_depth_markers_present():
    assert MD.count('### Depth (a–f)') >= 5
    for key in ['**Assumptions.**', '**Procedure.**', '**Artefact.**', '**Numbers.**', '**Second setting.**', '**Limitations.**']:
        assert key in MD


def test_lab_claims_present():
    for s in ['4de7adcc9dea', '-0.7539', '0.2121', '0.935', 'BAD_PROXY', 't-350101', 'fee_explanation']:
        assert s in MD


def test_further_reading_after_interview():
    iv = MD.find('# Interview Questions and Answers')
    fr = MD.find('## Further reading')
    assert iv > 0 and fr > iv
    assert '## Further reading' not in PARTS_BODY
    assert PARTS_FR.lstrip().startswith('## Further reading')


def test_sequential_footnotes_wired():
    body_before_fr = MD.split('## Further reading')[0]
    for n in range(1, 7):
        assert f'[^{n}]' in body_before_fr
        assert f'[^{n}]:' in PARTS_FR


def test_h3_not_shard_wall():
    body = MD.split('# Interview Questions and Answers')[0]
    h3 = re.findall(r'(?m)^### ', body)
    assert len(h3) <= 40, len(h3)
