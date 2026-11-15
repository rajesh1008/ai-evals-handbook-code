"""AppTest for the annotation screen: the reply is hidden before saving, shown after, and the break prompt
appears past 45 minutes."""
from streamlit.testing.v1 import AppTest


def test_blind_reveal_and_break():
    at = AppTest.from_file("app.py", default_timeout=60)
    at.query_params["annotator"] = "kevin"
    at.run()
    assert not any("Compass replied" in i.value for i in at.info)
    at.radio[0].set_value("draft_deferral").run()
    at.text_input[0].set_value("G-07 no self-employment stated").run()
    at.button[0].click().run()
    assert any("Compass replied" in i.value for i in at.info)
    assert not at.warning
    at2 = AppTest.from_file("app.py", default_timeout=60)
    at2.query_params["annotator"] = "kevin"; at2.query_params["offset"] = "50"
    at2.run()
    assert at2.warning and "45 minutes" in at2.warning[0].value
