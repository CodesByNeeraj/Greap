"""Recommendations from purchase history (FR-7.3)."""

from collections import Counter

from greap.constants import ENTRY_ORDERED, ENTRY_PAID
from greap.context_store import ContextStore

MAX_RECOMMENDATIONS = 3
REPEAT_THRESHOLD = 2


def recommendationsFor(store: ContextStore, telegramId: str) -> list[str]:
    """Items bought regularly first, then the most recent purchases."""
    bought = [
        store.getQueue(e["queueId"])["name"]
        for e in store.entriesForUser(telegramId)
        if e["status"] in (ENTRY_PAID, ENTRY_ORDERED)
    ]
    regular = [n for n, c in Counter(bought).most_common() if c >= REPEAT_THRESHOLD]
    recent = list(dict.fromkeys(reversed(bought)))
    return list(dict.fromkeys(regular + recent))[:MAX_RECOMMENDATIONS]
