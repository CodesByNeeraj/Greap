"""The agent must never show the same line twice in a row."""

from greap.greap_agent import removeRepeatedLines


def test_repeated_question_is_collapsed():
    text = "What do you want to buy?\nWhat do you want to buy?"
    assert removeRepeatedLines(text) == "What do you want to buy?"


def test_distinct_lines_and_blank_lines_are_kept():
    text = "Rice A: SGD 5\n\nRice B: SGD 6"
    assert removeRepeatedLines(text) == text
