"""Time-driven queue rules: unpaid expiry (FR-5.7) and the sad flow (section 6)."""

from datetime import datetime, timedelta
from typing import Any

from greap.clock import fromIso, toIso
from greap.constants import CHOICE_BUY_REMAINING, CHOICE_CANCEL
from greap.constants import ENTRY_CANCELLED, ENTRY_EXPIRED, ENTRY_LOCKED, ENTRY_PAID
from greap.constants import PAYMENT_WINDOW_HOURS, QUEUE_CLOSED
from greap.constants import QUEUE_DEADLINE_DAYS, QUEUE_LOCKED, QUEUE_OPEN, QUEUE_SHORT
from greap.context_store import ContextStore
from greap.money import formatMoney, lineTotal
from greap.queue_engine import lockQueue

Notice = tuple[str, str]  # (telegramId, message)


def expireUnpaid(store: ContextStore, now: datetime) -> list[Notice]:
    """Unpaid entries cancel after 24h and the queue reopens with free units."""
    notices: list[Notice] = []
    for queue in list(store.data["queues"].values()):
        if queue["status"] != QUEUE_LOCKED:
            continue
        if now < fromIso(queue["lockedAt"]) + timedelta(hours=PAYMENT_WINDOW_HOURS):
            continue
        for entry in store.liveEntriesForQueue(queue["id"]):
            if entry["status"] == ENTRY_LOCKED:
                entry["status"] = ENTRY_EXPIRED
                queue["unitsFilled"] -= entry["units"]
                notices.append(
                    (entry["telegramId"], f"Your {queue['name']} entry expired unpaid.")
                )
        queue["status"] = QUEUE_OPEN if queue["unitsFilled"] > 0 else QUEUE_CLOSED
        queue["deadline"] = toIso(now + timedelta(days=QUEUE_DEADLINE_DAYS))
    store.save()
    return notices


def markShortQueues(store: ContextStore, now: datetime) -> list[Notice]:
    """At the deadline, tell each user the queue is short and offer 3 choices."""
    notices: list[Notice] = []
    for queue in store.data["queues"].values():
        if queue["status"] != QUEUE_OPEN or now < fromIso(queue["deadline"]):
            continue
        queue["status"] = QUEUE_SHORT
        remaining = queue["cartonSize"] - queue["unitsFilled"]
        for entry in store.liveEntriesForQueue(queue["id"]):
            entry.pop("decision", None)
            notices.append((entry["telegramId"], shortMessage(queue, remaining)))
    store.save()
    return notices


def shortMessage(queue: dict[str, Any], remaining: int) -> str:
    """FR-6.1 and FR-6.2 wording, including the three choices."""
    return (
        f"{queue['name']} reached {queue['unitsFilled']}/{queue['cartonSize']}. "
        f"Choose: buy the remaining {remaining} units, extend {QUEUE_DEADLINE_DAYS} "
        "more days, or cancel."
    )


def applyChoice(
    store: ContextStore, entry: dict, choice: str, now: datetime
) -> list[Notice]:
    """Record one user's sad-flow choice, then settle the queue if it can be."""
    queue = store.getQueue(entry["queueId"])
    if choice == CHOICE_BUY_REMAINING:
        return buyRemaining(store, queue, entry, now)
    entry["decision"] = choice
    if choice == CHOICE_CANCEL:
        entry["status"] = ENTRY_CANCELLED
        queue["unitsFilled"] -= entry["units"]
    notices = settleIfAllDecided(store, queue, now)
    store.save()
    return notices


def buyRemaining(
    store: ContextStore, queue: dict, entry: dict, now: datetime
) -> list[Notice]:
    """First taker adds the missing units and the queue locks (FR-6.3)."""
    remaining = queue["cartonSize"] - queue["unitsFilled"]
    entry["units"] += remaining
    entry["total"] = lineTotal(entry["unitPrice"], entry["units"])
    queue["unitsFilled"] = queue["cartonSize"]
    lockQueue(store, queue, now)
    store.save()
    return lockNotices(store, queue)


def lockNotices(store: ContextStore, queue: dict) -> list[Notice]:
    """FR-5.1: tell every locked user the product, units, unit price and total."""
    return [
        (
            e["telegramId"],
            f"{queue['name']} is full. You owe "
            f"{formatMoney(e['total'], queue['currency'])} "
            f"({e['units']} x {formatMoney(e['unitPrice'], queue['currency'])}). "
            "Use /pay within 24 hours.",
        )
        for e in store.liveEntriesForQueue(queue["id"])
        if e["status"] == ENTRY_LOCKED
    ]


def settleIfAllDecided(store: ContextStore, queue: dict, now: datetime) -> list[Notice]:
    """Close the queue if everyone cancelled, else extend once all have chosen."""
    live = [
        e for e in store.liveEntriesForQueue(queue["id"]) if e["status"] != ENTRY_PAID
    ]
    if not live:
        queue["status"] = QUEUE_CLOSED
        return []
    if any(e.get("decision") is None for e in live):
        return []
    queue["status"] = QUEUE_OPEN
    queue["deadline"] = toIso(now + timedelta(days=QUEUE_DEADLINE_DAYS))
    return [
        (e["telegramId"], f"{queue['name']} extended {QUEUE_DEADLINE_DAYS} days.")
        for e in live
    ]
