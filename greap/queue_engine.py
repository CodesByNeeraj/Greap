"""Queue rules from PRD sections 3 and 4: join, overflow, lock, cancel, change."""

from datetime import datetime, timedelta
from typing import Any

from greap.clock import toIso
from greap.constants import ENTRY_CANCELLED, ENTRY_LOCKED, ENTRY_QUEUED
from greap.constants import QUEUE_CLOSED, QUEUE_DEADLINE_DAYS, QUEUE_LOCKED
from greap.constants import QUEUE_OPEN, TYPE_DIRECT, TYPE_QUEUE
from greap.context_store import ContextStore
from greap.money import lineTotal, unitPriceOf


def splitUnits(freeSpace: int, cartonSize: int, units: int) -> list[int]:
    """Split a join into per-carton chunks (FR-3.4).

    10 units into 6 free spaces gives [6, 4]: 6 finish this carton and 4 start
    the next one.
    """
    chunks: list[int] = []
    remaining = units
    space = freeSpace
    while remaining > 0:
        chunk = min(space, remaining)
        chunks.append(chunk)
        remaining -= chunk
        space = cartonSize
    return chunks


def freeSpaceFor(store: ContextStore, product: dict[str, Any]) -> int:
    """Units still needed in the open queue, or a whole carton if none is open."""
    queue = store.openQueueFor(product["productId"])
    return (
        queue["cartonSize"] - queue["unitsFilled"] if queue else product["cartonSize"]
    )


def newQueue(store: ContextStore, product: dict[str, Any], now: datetime) -> dict:
    """Open a queue; its deadline starts at its first entry (FR-4.2)."""
    queue = {
        "id": store.newId("q"),
        "productId": product["productId"],
        "variantId": product["variantId"],
        "name": product["name"],
        "merchant": product["merchant"],
        "currency": product["currency"],
        "cartonSize": product["cartonSize"],
        "cartonPrice": product["cartonPrice"],
        "cartons": 1,
        "unitsFilled": 0,
        "status": QUEUE_OPEN,
        "deadline": toIso(now + timedelta(days=QUEUE_DEADLINE_DAYS)),
        "lockedAt": None,
    }
    store.data["queues"][queue["id"]] = queue
    return queue


def newEntry(
    store: ContextStore, telegramId: str, queue: dict, units: int, entryType: str
) -> dict:
    """Price an entry at the queue's unit price (FR-3.5)."""
    unitPrice = unitPriceOf(queue["cartonPrice"], queue["cartonSize"])
    entry = {
        "id": store.newId("e"),
        "telegramId": telegramId,
        "queueId": queue["id"],
        "type": entryType,
        "units": units,
        "unitPrice": unitPrice,
        "total": lineTotal(unitPrice, units),
        "status": ENTRY_QUEUED,
    }
    store.data["entries"][entry["id"]] = entry
    return entry


def lockQueue(store: ContextStore, queue: dict, now: datetime) -> None:
    """A full carton locks and its entries move to the happy flow (FR-4.4)."""
    queue["status"] = QUEUE_LOCKED
    queue["lockedAt"] = toIso(now)
    for entry in store.liveEntriesForQueue(queue["id"]):
        if entry["status"] == ENTRY_QUEUED:
            entry["status"] = ENTRY_LOCKED


def joinQueue(
    store: ContextStore, telegramId: str, product: dict, units: int, now: datetime
) -> list[dict]:
    """Add units, spilling extra units into the next carton's queue (FR-4.5)."""
    created: list[dict] = []
    for chunk in splitUnits(freeSpaceFor(store, product), product["cartonSize"], units):
        queue = store.openQueueFor(product["productId"]) or newQueue(
            store, product, now
        )
        created.append(newEntry(store, telegramId, queue, chunk, TYPE_QUEUE))
        queue["unitsFilled"] += chunk
        if queue["unitsFilled"] >= queue["cartonSize"]:
            lockQueue(store, queue, now)
    store.save()
    return created


def buyDirect(
    store: ContextStore, telegramId: str, product: dict, cartons: int, now: datetime
) -> dict:
    """Whole cartons skip the queue: a pre-locked queue holds the one entry."""
    queue = newQueue(store, product, now)
    queue["cartons"] = cartons
    queue["unitsFilled"] = product["cartonSize"] * cartons
    entry = newEntry(store, telegramId, queue, queue["unitsFilled"], TYPE_DIRECT)
    lockQueue(store, queue, now)
    store.save()
    return entry


def cancelEntry(store: ContextStore, entryId: str, telegramId: str) -> str:
    """Only queued entries can be cancelled (FR-8.3). Returns an error or ''."""
    entry = store.getEntry(entryId)
    if not entry or entry["telegramId"] != telegramId:
        return "No such entry for this user."
    if entry["status"] != ENTRY_QUEUED:
        return f"Entry is {entry['status']}, so it cannot be cancelled."
    queue = store.getQueue(entry["queueId"])
    entry["status"] = ENTRY_CANCELLED
    queue["unitsFilled"] -= entry["units"]
    if queue["unitsFilled"] <= 0:
        queue["status"] = QUEUE_CLOSED
    store.save()
    return ""


def changeUnits(store: ContextStore, entryId: str, telegramId: str, units: int) -> str:
    """Change units on a queued entry without overflowing the carton (FR-8.2)."""
    entry = store.getEntry(entryId)
    if not entry or entry["telegramId"] != telegramId:
        return "No such entry for this user."
    if entry["status"] != ENTRY_QUEUED or units < 1:
        return "Only queued entries can change, and units must be at least 1."
    queue = store.getQueue(entry["queueId"])
    newFilled = queue["unitsFilled"] - entry["units"] + units
    if newFilled > queue["cartonSize"]:
        return f"That would overfill the carton. Max is {queue['cartonSize']} units."
    queue["unitsFilled"] = newFilled
    entry["units"] = units
    entry["total"] = lineTotal(entry["unitPrice"], units)
    store.save()
    return ""
