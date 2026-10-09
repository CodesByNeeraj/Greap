"""Long product lists must be split without breaking a line."""

from greap.constants import TELEGRAM_MESSAGE_LIMIT
from greap.telegram_bot import splitForTelegram


def test_short_text_is_one_message():
    assert splitForTelegram("hello\nworld") == ["hello\nworld"]


def test_long_text_splits_on_lines_under_the_limit():
    text = "\n".join(f"product {i}: " + "x" * 80 for i in range(200))
    chunks = splitForTelegram(text)
    assert len(chunks) > 1
    assert all(len(c) <= TELEGRAM_MESSAGE_LIMIT for c in chunks)
    assert "\n".join(chunks) == text
