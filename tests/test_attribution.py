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
    first, second = extract_quotes(text)
    present = ["baifengyuan", "muwanhe"]

    first_attribution = attribute_quote(
        first, text, DEFAULT_CHARACTERS, None, present
    )
    second_attribution = attribute_quote(
        second, text, DEFAULT_CHARACTERS, first_attribution.speaker_id, present
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
