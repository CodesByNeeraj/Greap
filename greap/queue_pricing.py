"""FR-4.7: keep queue prices in step with Reap and tell affected users."""

from greap.constants import ENTRY_LOCKED, ENTRY_QUEUED
from greap.context_store import ContextStore
from greap.money import formatMoney, lineTotal, unitPriceOf
from greap.queue_deadlines import Notice


def applyPriceChange(
    store: ContextStore, queue: dict, newCartonPrice: float
) -> list[Notice]:
    """Reprice an open queue; entries are repriced so totals stay consistent."""
    if newCartonPrice == queue["cartonPrice"]:
        return []
    queue["cartonPrice"] = newCartonPrice
    unitPrice = unitPriceOf(newCartonPrice, queue["cartonSize"])
    notices: list[Notice] = []
    for entry in store.liveEntriesForQueue(queue["id"]):
        if entry["status"] not in (ENTRY_QUEUED, ENTRY_LOCKED):
            continue
        entry["unitPrice"] = unitPrice
        entry["total"] = lineTotal(unitPrice, entry["units"])
        notices.append(
            (
                entry["telegramId"],
                f"Price changed for {queue['name']}: now "
                f"{formatMoney(unitPrice, queue['currency'])} per unit "
                f"({formatMoney(entry['total'], queue['currency'])} for your "
                f"{entry['units']}). Ask me to cancel it if you no longer want it.",
            )
        )
    store.save()
    return notices
