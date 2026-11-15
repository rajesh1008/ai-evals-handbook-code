"""Chapter 4: the Test Pyramid (Truss v0.7).

Every Truss check carries a layer (1-5), the verification stream it belongs
to, an owner, the stages it is allowed to run at, and a cost model. A suite
can then be run, timed and priced layer by layer, and linted for the most
expensive mistake in this chapter: a slow, paid, non-deterministic check
wired into a gate that runs on every commit.
"""
import time
from dataclasses import dataclass, field

LAYERS = {
    1: "unit checks on deterministic code",
    2: "component evals on labelled fixtures",
    3: "judge-scored task evals on sampled traces",
    4: "trajectory and end-to-end evals with simulated users",
    5: "shadow and online measurement",
}
STREAMS = ("code tests", "component evals", "judge evals", "human review", "statistics", "online")
# Stages in order of falling frequency, and the highest layer each may run.
STAGES = ("commit", "pull_request", "release", "shadow", "weekly")
MAX_LAYER = {"commit": 1, "pull_request": 2, "release": 4, "shadow": 5, "weekly": 5}
# Streams whose verdicts can differ between two runs on the same input.
NONDETERMINISTIC = {"judge evals", "human review", "online"}


@dataclass
class Cost:
    """Cost of checking one item: tokens at the model's prices, people's
    minutes at their loaded rate, and machine seconds at the runner's rate."""
    input_tokens: float = 0
    output_tokens: float = 0
    human_minutes: float = 0
    human_rate: float = 0          # dollars an hour, loaded
    cpu_seconds: float = 0

    def dollars(self, items, prices):
        model = items * (self.input_tokens * prices["input_per_m"]
                         + self.output_tokens * prices["output_per_m"]) / 1e6
        people = items * self.human_minutes / 60 * self.human_rate
        machine = items * self.cpu_seconds / 60 * prices["runner_per_min"]
        return model + people + machine


@dataclass
class Check:
    name: str
    layer: int
    stream: str
    owner: str
    stages: tuple
    fn: object = None              # fn(ctx) -> (items, failures, detail)
    cost: Cost = field(default_factory=Cost)
    blocking: bool = True

    def __post_init__(self):
        if self.layer not in LAYERS:
            raise ValueError(f"{self.name}: layer must be 1-5, got {self.layer}")
        if self.stream not in STREAMS:
            raise ValueError(f"{self.name}: unknown stream {self.stream!r}")
        bad = [s for s in self.stages if s not in STAGES]
        if bad:
            raise ValueError(f"{self.name}: unknown stage {bad}")


@dataclass
class Result:
    check: Check
    items: int
    failures: int
    seconds: float
    dollars: float
    detail: str = ""

    @property
    def passed(self):
        return self.failures == 0


class Suite:
    def __init__(self, prices):
        self.prices = prices
        self.checks = []

    def add(self, check):
        if any(c.name == check.name for c in self.checks):
            raise ValueError(f"duplicate check {check.name}")
        self.checks.append(check)
        return check

    def check(self, name, layer, stream, owner, stages, cost=None, blocking=True):
        """Decorator form: @suite.check("fee rule", 1, "code tests", ...)."""
        def wrap(fn):
            self.add(Check(name, layer, stream, owner, tuple(stages), fn, cost or Cost(), blocking))
            return fn
        return wrap

    def at(self, stage):
        return [c for c in self.checks if stage in c.stages]

    def by_layer(self):
        out = {k: [] for k in LAYERS}
        for c in self.checks:
            out[c.layer].append(c)
        return out

    def run(self, stage, ctx, layers=None, fail_fast=True):
        """Run the checks for a stage, lowest layer first. With fail_fast, a
        blocking failure stops the higher layers from running and spending."""
        results = []
        for layer in sorted(LAYERS):
            if layers and layer not in layers:
                continue
            batch = [c for c in self.at(stage) if c.layer == layer]
            for c in batch:
                t0 = time.perf_counter()
                items, failures, detail = c.fn(ctx)
                secs = time.perf_counter() - t0
                results.append(Result(c, items, failures, secs, c.cost.dollars(items, self.prices), detail))
            if fail_fast and any(r.failures and r.check.blocking for r in results if r.check.layer == layer):
                break
        return results


def lint(suite):
    """Placement problems: a check at a stage above its layer's ceiling, or a
    non-deterministic stream blocking a commit."""
    problems = []
    for c in suite.checks:
        for s in c.stages:
            if c.layer > MAX_LAYER[s]:
                problems.append(f"{c.name}: layer {c.layer} check runs at '{s}' (ceiling is layer {MAX_LAYER[s]})")
            if s == "commit" and c.blocking and c.stream in NONDETERMINISTIC:
                problems.append(f"{c.name}: '{c.stream}' verdicts vary run to run but block every commit")
    return problems


def monthly_bill(suite, runs_per_month, items):
    """Dollars a month per layer: each check's cost per run times how often its
    stages run. items maps check name -> items per run."""
    bill = {k: 0.0 for k in LAYERS}
    for c in suite.checks:
        n = sum(runs_per_month.get(s, 0) for s in c.stages)
        bill[c.layer] += n * c.cost.dollars(items.get(c.name, 0), suite.prices)
    return bill


def summarise(results):
    """Per layer: checks run, items, failures, seconds, dollars."""
    out = {}
    for r in results:
        s = out.setdefault(r.check.layer, {"checks": 0, "items": 0, "failures": 0, "seconds": 0.0, "dollars": 0.0})
        s["checks"] += 1
        s["items"] += r.items
        s["failures"] += r.failures
        s["seconds"] += r.seconds
        s["dollars"] += r.dollars
    return out
