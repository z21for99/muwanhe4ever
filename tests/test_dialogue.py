from muwanhe.compiler.dialogue import extract_quotes


def test_extract_double_quotes():
    quotes = extract_quotes("“你好。”我说。")

    assert len(quotes) == 1
    assert quotes[0].text == "你好。"
    assert quotes[0].unclosed is False


def test_extract_book_quotes():
    quotes = extract_quotes("『注』")

    assert len(quotes) == 1
    assert quotes[0].text == "注"


def test_unclosed_quote_is_marked():
    quotes = extract_quotes("“没有结尾")

    assert len(quotes) == 1
    assert quotes[0].unclosed is True
