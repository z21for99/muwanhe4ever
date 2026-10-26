from __future__ import annotations

from dataclasses import dataclass

OPENERS = {"“": "”", "「": "」", "『": "』"}


@dataclass(frozen=True)
class Quote:
    text: str
    start: int
    end: int
    raw: str
    unclosed: bool


def extract_quotes(text: str) -> list[Quote]:
    quotes: list[Quote] = []
    index = 0
    length = len(text)

    while index < length:
        opener = text[index]
        if opener not in OPENERS:
            index += 1
            continue

        closer = OPENERS[opener]
        end = text.find(closer, index + 1)
        if end == -1:
            paragraph = text.find("\n\n", index + 1)
            if paragraph == -1:
                paragraph = length
            quotes.append(
                Quote(
                    text=text[index + 1 : paragraph],
                    start=index,
                    end=paragraph,
                    raw=text[index:paragraph],
                    unclosed=True,
                )
            )
            index = paragraph
        else:
            quotes.append(
                Quote(
                    text=text[index + 1 : end],
                    start=index,
                    end=end + 1,
                    raw=text[index : end + 1],
                    unclosed=False,
                )
            )
            index = end + 1

    return quotes
