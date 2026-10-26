from muwanhe.characters import DEFAULT_CHARACTERS
from muwanhe.compiler.attribution import attribute_quote
from muwanhe.compiler.dialogue import extract_quotes


def test_cue_after_quote():
    text = "“你好。”我说。"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote, text, DEFAULT_CHARACTERS, None, ["baifengyuan"]
    )

    assert attribution.speaker_id == "baifengyuan"
    assert attribution.method == "cue"


def test_cue_before_quote():
    text = "她轻声道：“过来。”"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote, text, DEFAULT_CHARACTERS, None, ["baifengyuan", "muwanhe"]
    )

    assert attribution.speaker_id == "muwanhe"
    assert attribution.method == "cue"


def test_turn_taking():
    text = "“你好。”\n“你也好。”"
    _first, second = extract_quotes(text)
    present = ["baifengyuan", "muwanhe"]

    second_attribution = attribute_quote(
        second, text, DEFAULT_CHARACTERS, "baifengyuan", present
    )

    assert second_attribution.speaker_id == "muwanhe"
    assert second_attribution.method == "turn"


def test_addressee_pair():
    text = "我对她说：“走。”"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote, text, DEFAULT_CHARACTERS, None, ["baifengyuan"]
    )

    assert attribution.speaker_id == "baifengyuan"
    assert attribution.addressee_id == "muwanhe"


def test_father_cue():
    text = "父亲说：“饭呢？”"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote, text, DEFAULT_CHARACTERS, None, ["baifengyuan", "father"]
    )

    assert attribution.speaker_id == "father"


def test_voice_cue():
    text = "“饭呢？”……父亲那公鸭嗓子般的声音……"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote,
        text,
        DEFAULT_CHARACTERS,
        None,
        ["baifengyuan", "muwanhe", "father"],
    )

    assert attribution.speaker_id == "father"
    assert attribution.method == "voice"


def test_vocative():
    text = "“儿子，你回来啦。”"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote,
        text,
        DEFAULT_CHARACTERS,
        None,
        ["baifengyuan", "muwanhe"],
    )

    assert attribution.speaker_id == "muwanhe"
    assert attribution.addressee_id == "baifengyuan"
    assert attribution.method == "vocative"


def test_verb_first_cue():
    text = "“下面我自己来。”说完，我拿过毛巾。"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote, text, DEFAULT_CHARACTERS, None, ["baifengyuan", "muwanhe"]
    )

    assert attribution.speaker_id == "baifengyuan"
    assert attribution.method == "cue"


def test_answer_cue():
    text = "“我来收碗。”她回答了一句。"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote, text, DEFAULT_CHARACTERS, None, ["baifengyuan", "muwanhe"]
    )

    assert attribution.speaker_id == "muwanhe"
    assert attribution.method == "cue"


def test_voice_after_long_window():
    text = "“饭呢？”" + " " * 35 + "父亲那公鸭嗓子般的声音。"
    quote = extract_quotes(text)[0]

    attribution = attribute_quote(
        quote, text, DEFAULT_CHARACTERS, None, ["baifengyuan", "father"]
    )

    assert attribution.speaker_id == "father"
    assert attribution.method == "voice"
