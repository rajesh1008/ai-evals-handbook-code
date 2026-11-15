"""Chapter 3: the trace contract, and its mapping onto OpenTelemetry GenAI.

A trace is fit to evaluate when a reader who was not there can say what the
assistant saw, what it did, under which settings and documents, and what
happened afterwards. The contract below names those fields; `gaps()` lists
what a stored trace is missing, and `to_otel()` renames a Truss span into the
OpenTelemetry GenAI semantic conventions so the schema travels.
"""
SCHEMA_VERSION = "0.5"

TRACE_FIELDS = [
    "trace_id", "conversation_id", "schema_version", "started_at_utc", "channel",
    "flow", "router_version", "model_id", "temperature", "prompt_version",
    "policy_corpus_version", "borrower_token", "loan_token", "state",
]

SPAN_FIELDS = {
    "invoke_agent": ["agent_name"],
    "chat": ["model_id", "input", "output", "input_tokens", "output_tokens", "latency_ms"],
    "execute_tool": ["tool_name", "call_id", "arguments", "result", "status", "latency_ms"],
    "retrieve": ["doc_ids", "doc_versions", "query"],
    "handoff": ["reason", "queue"],
}

# What a reader needs, per flow, to judge the reply against policy.
EVIDENCE = {
    "account_question": ["balance", "as_of"],
    "fee_explanation": ["fee_amount", "days_late", "grace_days", "schedule_version"],
    "statement_request": ["period"],
    "payoff_letter": ["payoff_amount", "good_through", "per_diem"],
    "lien_release": ["paid_in_full_on", "title_state"],
    "hardship": ["loan_amount", "monthly_payment", "stated_income", "prior_deferral_on",
                 "policy_version"],
}

OTEL = {  # Truss name -> OpenTelemetry GenAI attribute (or harbor.* where none exists)
    "trace_id": "trace_id (span context)",
    "conversation_id": "gen_ai.conversation.id",
    "model_id": "gen_ai.request.model",
    "temperature": "gen_ai.request.temperature",
    "input_tokens": "gen_ai.usage.input_tokens",
    "output_tokens": "gen_ai.usage.output_tokens",
    "agent_name": "gen_ai.agent.name",
    "tool_name": "gen_ai.tool.name",
    "call_id": "gen_ai.tool.call.id",
    "arguments": "gen_ai.tool.call.arguments (opt-in)",
    "result": "gen_ai.tool.call.result (opt-in)",
    "status": "error.type when failed",
    "prompt_version": "harbor.prompt.version",
    "policy_corpus_version": "harbor.policy.corpus_version",
    "doc_versions": "harbor.retrieval.doc_versions",
    "flow": "harbor.flow",
}

OPERATION = {"invoke_agent": "invoke_agent", "chat": "chat", "execute_tool": "execute_tool",
             "retrieve": "execute_tool", "handoff": "execute_tool"}


def gaps(trace, spans):
    """Fields the contract requires that this trace or its spans lack."""
    missing = [f"trace.{f}" for f in TRACE_FIELDS if trace.get(f) in (None, "")]
    for s in spans:
        for f in SPAN_FIELDS.get(s["kind"], []):
            if s.get("attrs", {}).get(f) in (None, ""):
                missing.append(f"{s['kind']}:{s.get('name', '')}.{f}")
    return missing


def evidence_present(flow, evidence):
    """Which evidence fields for the flow survive in a dict of extracted values."""
    return {f: evidence.get(f) not in (None, "", "[REDACTED]") for f in EVIDENCE[flow]}


def to_otel(span):
    """Rename a Truss span into OpenTelemetry GenAI attribute names."""
    op = OPERATION[span["kind"]]
    name = f"{op} {span['attrs'].get('tool_name') or span['attrs'].get('agent_name') or span['attrs'].get('model_id', '')}".strip()
    out = {"name": name, "gen_ai.operation.name": op}
    for k, v in span["attrs"].items():
        if k == "status":
            if v != "ok":
                out["error.type"] = v
            continue
        out[OTEL.get(k, f"harbor.{k}").split(" ")[0]] = v
    if span["kind"] == "retrieve":
        out["gen_ai.tool.type"] = "datastore"
    return out
