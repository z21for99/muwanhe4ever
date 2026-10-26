from muwanhe.providers.llm import FakeLLM, extract_json


def test_extract_json_fenced():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_surrounding_text():
    assert extract_json('prefix {"a": 2} suffix') == {"a": 2}


def test_fake_llm_records_calls():
    fake = FakeLLM({"ok": True})

    assert fake.complete_json("system", "user") == {"ok": True}
    assert fake.calls == [("system", "user")]
