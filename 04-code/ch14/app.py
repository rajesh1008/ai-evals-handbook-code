"""Chapter 14 annotation screen (Streamlit). Run: streamlit run app.py -- then open ?annotator=marisol
One trace at a time from the reader's queue; anchors look like any other trace; Compass's reply stays hidden
until the label is saved (the blind two-step reveal); the guideline is shown by sentence ID so a reason
can cite one; a break prompt appears after 45 minutes in a sitting. Labels go to out/labels.jsonl."""
import json
import time
from pathlib import Path

import streamlit as st

import fixture as F
import guideline as G
import lab

OUT = Path(__file__).resolve().parent / "out/labels.jsonl"
VERSION = "ops-1.1"


@st.cache_data
def queue(reader, week):
    weeks = lab.run()
    wk = weeks[week - 1]
    W = F.build()
    by = {t["trace_id"]: t for t in W[week - 1] + lab.ANCHORS}
    return [by[t] for t in sorted(wk["readings"]) if reader in wk["readings"][t]]


reader = st.query_params.get("annotator", "marisol")
week = int(st.query_params.get("week", "2"))
q = queue(reader, week)
ss = st.session_state
ss.setdefault("i", 0); ss.setdefault("saved", False); ss.setdefault("start", time.time())
if ss.i >= len(q):
    st.success("Queue finished for this week."); st.stop()
t = q[ss.i]
minutes_in = (time.time() - ss.start) / 60 + float(st.query_params.get("offset", "0"))
st.caption(f"{reader} | guideline {VERSION} | trace {ss.i + 1} of {len(q)} | {minutes_in:.0f} minutes this sitting")
if minutes_in > 45:
    st.warning("You have been reading for more than 45 minutes. Take a ten-minute break before the next trace.")
left, right = st.columns([3, 2])
with left:
    st.code(t["text"], language=None)
    label = st.radio("First-reply action the policy requires", F.LABELS, index=None, key=f"lab{ss.i}")
    reason = st.text_input("One line of reason (cite a sentence ID, e.g. G-06)", key=f"why{ss.i}")
    policy_q = st.checkbox("Policy question (the written policy seems wrong for this case)", key=f"pq{ss.i}")
    missing = st.text_input("Missing fact (only for cannot_tell)", key=f"mf{ss.i}") if label == "cannot_tell" else ""
    if st.button("Save label", disabled=label is None or not reason or ss.saved):
        with OUT.open("a") as fh:
            fh.write(json.dumps({"trace_id": t["trace_id"], "reader": reader, "label": label, "reason": reason,
                                 "policy_question": policy_q, "missing": missing, "guideline": VERSION,
                                 "minute_in_sitting": round(minutes_in, 1)}) + "\n")
        ss.saved = True
    if ss.saved:
        st.info(f"Compass replied: {F.SHORT[t['compass']]}. Your label is saved and cannot be changed here; "
                "if the reply changes your mind, tick policy question on the next screen or tell the adjudicator.")
        if st.button("Next trace"):
            ss.i += 1; ss.saved = False; st.rerun()
with right:
    st.subheader("Guideline")
    for k, v in G.VERSIONS[VERSION].items():
        st.markdown(f"**{k}** {v}")
