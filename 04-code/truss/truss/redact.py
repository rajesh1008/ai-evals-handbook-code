"""Chapter 3: redaction before storage, with a check on what it costs.

Identity is replaced by stable keyed tokens (the same borrower always maps to
the same token, so joins survive). Evidence the evaluator needs is kept. Every
rule change is run against `evidence_report()` before it ships, because a rule
that removes evidence makes traces unjudgeable without anyone noticing.
"""
import hashlib
import hmac
import re

IDENTITY = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "phone": re.compile(r"\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "account": re.compile(r"\b\d{10,12}\b"),
}
# A looser scan used only to audit what slipped through (never to redact).
AUDIT = {"ssn_like": re.compile(r"\b\d{3}[ .]?\d{2}[ .]?\d{4}\b")}


class Redactor:
    def __init__(self, key=b"harbor-fixture-key", extra_rules=None):
        self.key = key
        self.rules = dict(IDENTITY)
        self.rules.update(extra_rules or {})

    def token(self, kind, value):
        digest = hmac.new(self.key, f"{kind}|{value}".encode(), hashlib.sha256).hexdigest()[:8]
        return f"{kind.upper()}_{digest}"

    def text(self, s, names=()):
        for n in names:
            s = s.replace(n, self.token("name", n))
        for kind, rx in self.rules.items():
            s = rx.sub(lambda m, k=kind: self.token(k, m.group(0)) if k in IDENTITY else "[REDACTED]", s)
        return s

    def value(self, v):
        """Apply the free-text rules to one structured evidence value."""
        return self.text(str(v)) if v is not None else None


def residual(text):
    """Strings that look like identity data after redaction (audit only)."""
    return [m.group(0) for rx in AUDIT.values() for m in rx.finditer(text)]


def evidence_report(redactor, cases):
    """cases: [(flow, {field: value})]. Share of cases per flow whose evidence survives."""
    from .schema import EVIDENCE
    out = {}
    for flow, ev in cases:
        kept = all(redactor.value(ev[f]) == str(ev[f]) for f in EVIDENCE[flow] if ev.get(f) is not None)
        k, n = out.get(flow, (0, 0))
        out[flow] = (k + kept, n + 1)
    return out
