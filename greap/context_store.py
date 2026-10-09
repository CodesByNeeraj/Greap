"""Context: the single source of truth read by every agent (FR-7.5 to FR-7.7)."""

import json
import os
import uuid
from pathlib import Path
from typing import Any

from greap.constants import ENTRY_CANCELLED, ENTRY_EXPIRED, QUEUE_OPEN
from greap.markdown_views import writeUserViews

STORE_FILE_NAME = "context.json"
EMPTY_DATA: dict[str, Any] = {
    "users": {},
    "classifications": {},
    "queues": {},
    "entries": {},
}


class ContextStore:
    """JSON-file store. Everything runs in one asyncio loop, so no locking."""

    def __init__(self, dataDir: Path) -> None:
        self.dataDir = dataDir
        self.path = dataDir / STORE_FILE_NAME
        self.data = self.load()

    def load(self) -> dict[str, Any]:
        """Start empty on first run instead of requiring a setup step."""
        if not self.path.exists():
            return json.loads(json.dumps(EMPTY_DATA))
        return json.loads(self.path.read_text())

    def save(self) -> None:
        """Write atomically so a crash mid-write cannot corrupt the store."""
        self.dataDir.mkdir(parents=True, exist_ok=True)
        tempPath = self.path.with_suffix(".tmp")
        tempPath.write_text(json.dumps(self.data, indent=2))
        os.replace(tempPath, self.path)
        writeUserViews(self.dataDir, self)

    def newId(self, prefix: str) -> str:
        """Short readable ids, because users type entry ids into chat."""
        return f"{prefix}_{uuid.uuid4().hex[:6]}"

    def getUser(self, telegramId: str) -> dict[str, Any] | None:
        """FR-1.1: look a user up by Telegram id."""
        return self.data["users"].get(telegramId)

    def upsertUser(self, telegramId: str, **fields: Any) -> dict[str, Any]:
        """Create or partially update a profile (FR-1.4, FR-1.6)."""
        user = self.data["users"].setdefault(telegramId, {"telegramId": telegramId})
        user.update({key: value for key, value in fields.items() if value})
        self.save()
        return user

    def getClassification(self, productId: str) -> dict[str, Any] | None:
        """Cached per product id so the LLM is only asked once (FR-2.5)."""
        return self.data["classifications"].get(productId)

    def setClassification(self, productId: str, result: dict[str, Any]) -> None:
        """Remember an LLM classification."""
        self.data["classifications"][productId] = result
        self.save()

    def getQueue(self, queueId: str) -> dict[str, Any]:
        """Fetch a queue by id."""
        return self.data["queues"][queueId]

    def openQueueFor(self, productId: str) -> dict[str, Any] | None:
        """Each product has at most one open queue at a time (section 4)."""
        for queue in self.data["queues"].values():
            if queue["productId"] == productId and queue["status"] == QUEUE_OPEN:
                return queue
        return None

    def getEntry(self, entryId: str) -> dict[str, Any] | None:
        """Fetch an entry by id."""
        return self.data["entries"].get(entryId)

    def entriesForUser(self, telegramId: str) -> list[dict[str, Any]]:
        """All of one user's entries, newest last."""
        return [
            e for e in self.data["entries"].values() if e["telegramId"] == telegramId
        ]

    def liveEntriesForQueue(self, queueId: str) -> list[dict[str, Any]]:
        """Entries still taking part in a queue (not cancelled or expired)."""
        dead = (ENTRY_CANCELLED, ENTRY_EXPIRED)
        return [
            e
            for e in self.data["entries"].values()
            if e["queueId"] == queueId and e["status"] not in dead
        ]
