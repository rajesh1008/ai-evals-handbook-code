"""Blind labelling screen for the hardship gold set (Streamlit).
Run: GOLD_DB=out/gold.db GOLD_BATCH=session-1 GOLD_GUIDELINE=r2 streamlit run app.py
Open ?annotator=grace or ?annotator=ben to label; ?role=adjudicator to rule on disagreements.
A reader's screen shows the next trace in the batch and nothing about the other reader."""
import os
import time
from datetime import date

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "truss"))

import store
from guideline import REVISIONS
from fixture import LABELS

DB, BATCH, G = os.environ.get("GOLD_DB", "out/gold.db"), os.environ.get("GOLD_BATCH", "session-1"), os.environ.get("GOLD_GUIDELINE", "r2")
db = store.connect(DB)
qp = st.query_params
who, role = qp.get("annotator", ""), qp.get("role", "reader")
st.title("Hardship gold set")

if role == "adjudicator":
    dis = store.disagreements(db, G)
    st.write(f"{len(dis)} disagreements under guideline {G}")
    for d in dis[:1]:
        st.code(d["body"])
        st.write(f"Reader A: {d['A'][0]} ({d['A'][1]})  |  Reader B: {d['B'][0]} ({d['B'][1]})")
        st.radio("Gold", list(LABELS) + ["cannot_tell"], key="gold")
        st.radio("Kind", ["slip", "fact", "guideline", "policy"], key="kind")
        st.text_input("Rationale", key="why")
    st.stop()

if who not in ("grace", "ben"):
    st.error("Open the link from your invitation (it names you).")
    st.stop()
st.session_state.setdefault("start", time.time())
mins = (time.time() - st.session_state["start"]) / 60
if mins > 45:
    st.warning("You have been labelling for 45 minutes. Finish this trace and take a break.")
with st.expander(f"Guideline {G}"):
    for k, v in REVISIONS[G].items():
        st.markdown(f"**{k}** {v}")
row = store.next_trace(db, who, BATCH, G)
if row is None:
    st.success("Batch complete. Thank you.")
    st.stop()
tid, body = row
st.code(body)
label = st.radio("Action HP-2027-04 requires", list(LABELS) + ["cannot_tell"], key=f"lab-{tid}")
reason = st.text_input("One line of reason", key=f"why-{tid}")
pq = st.checkbox("Policy question", key=f"pq-{tid}")
if st.button("Save and next"):
    from truss.adjudication import Label
    store.save(db, Label(tid, who, label, G, round(mins, 2), f"{who}-{date.today()}", round(mins, 2),
                         date.today().isoformat(), reason, pq))
    st.rerun()
st.caption(f"Labels saved by you: {len(store.mine(db, who))}")
