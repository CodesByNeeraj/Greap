"""Per-user Cart and Past Purchase History markdown files (PRD section 7).

The JSON store is the source of truth; these files are readable views of it.
"""

from pathlib import Path
from typing import Any

from greap.constants import ENTRY_LOCKED, ENTRY_ORDERED, ENTRY_PAID, ENTRY_QUEUED
from greap.money import formatMoney

CART_STATUSES = (ENTRY_QUEUED, ENTRY_LOCKED)
HISTORY_STATUSES = (ENTRY_PAID, ENTRY_ORDERED)


def renderEntryLine(entry: dict[str, Any], queue: dict[str, Any]) -> str:
    """One bullet per entry with everything a person needs to recognise it."""
    total = formatMoney(entry["total"], queue["currency"])
    return (
        f"- {queue['name']} ({queue['merchant']}): {entry['units']} units, "
        f"{total}, status {entry['status']}, entry {entry['id']}"
    )


def renderSection(title: str, lines: list[str]) -> str:
    """Empty sections still say so, so the file is never confusingly blank."""
    body = "\n".join(lines) if lines else "- Nothing yet."
    return f"# {title}\n\n{body}\n"


def writeUserViews(dataDir: Path, store: Any) -> None:
    """Rewrite every user's cart.md and history.md from the store."""
    for telegramId in store.data["users"]:
        entries = store.entriesForUser(telegramId)
        folder = dataDir / "users" / str(telegramId)
        folder.mkdir(parents=True, exist_ok=True)
        for fileName, title, statuses in (
            ("cart.md", "Cart", CART_STATUSES),
            ("history.md", "Past Purchase History", HISTORY_STATUSES),
        ):
            lines = [
                renderEntryLine(entry, store.getQueue(entry["queueId"]))
                for entry in entries
                if entry["status"] in statuses
            ]
            (folder / fileName).write_text(renderSection(title, lines))
