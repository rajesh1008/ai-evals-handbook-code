"""Chapter 2: a trace completeness check, run before anyone reads a trace.

A trace whose reply quotes account data must show the tool calls that
fetched it. The check compares each trace's tool calls with the calls its
flow always makes, so a logging fault is caught before it becomes a label.
"""
REQUIRED_TOOLS = {
    "account_question": ["get_account"],
    "fee_explanation": ["get_account", "get_fee_schedule"],
    "statement_request": ["get_account", "send_statement"],
    "payoff_letter": ["get_account", "get_payoff_quote"],
    "lien_release": ["get_account", "get_title_status"],
    "hardship": ["get_account", "get_account_history"],
}


def missing_tools(flow, tools_called):
    """Tool calls the flow always makes that this trace does not record."""
    return [t for t in REQUIRED_TOOLS[flow] if t not in tools_called]


def completeness(traces):
    """Split traces into (complete, incomplete) with the missing calls named."""
    ok, bad = [], []
    for t in traces:
        gap = missing_tools(t["flow"], t["tools"])
        (bad if gap else ok).append({**t, "missing": gap})
    return ok, bad
