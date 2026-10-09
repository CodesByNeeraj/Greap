"""Orchestrator Agent (FR-7.1 to FR-7.4): turns confirmed payments into orders."""

from typing import Any

from greap.constants import ENTRY_ORDERED, ENTRY_PAID, QUEUE_LOCKED, QUEUE_ORDERED
from greap.constants import QUEUE_ORDERING
from greap.context_store import ContextStore
from greap.notifier import Notifier
from greap.procurement_order import ProcurementOrder


class Orchestrator:
    """Receives payments, orders once everyone paid, and reports back."""

    def __init__(
        self,
        store: ContextStore,
        order: ProcurementOrder,
        notifier: Notifier,
        phone: str,
    ) -> None:
        self.store = store
        self.order = order
        self.notifier = notifier
        self.phone = phone

    async def onPayment(self, entry: dict[str, Any]) -> None:
        """FR-5.8: order only after every entry in the queue is paid."""
        queue = self.store.getQueue(entry["queueId"])
        live = self.store.liveEntriesForQueue(queue["id"])
        if queue["status"] != QUEUE_LOCKED or any(
            e["status"] != ENTRY_PAID for e in live
        ):
            return
        # Marked first so a second payment arriving mid-order cannot double-order.
        queue["status"] = QUEUE_ORDERING
        self.store.save()
        await self.placeAndReport(queue, live)

    async def placeAndReport(self, queue: dict, live: list[dict]) -> None:
        """FR-7.12: tell users whether the order worked."""
        buyer = self.store.getUser(live[0]["telegramId"])
        result = await self.order.placeOrder(queue, self.shippingAddress(buyer))
        if not result.success:
            queue["status"] = QUEUE_LOCKED
            self.store.save()
            await self.notifier.sendOps(
                f"Order failed for {queue['name']}: {result.error}"
            )
            await self.tell(
                live, f"Your {queue['name']} order hit a problem. We are on it."
            )
            return
        queue["status"] = QUEUE_ORDERED
        for entry in live:
            entry["status"] = ENTRY_ORDERED
        self.store.save()
        await self.tell(live, f"Ordered! {queue['name']} order id {result.orderId}.")

    async def tell(self, entries: list[dict], text: str) -> None:
        """Message each distinct user in the queue once."""
        for telegramId in dict.fromkeys(e["telegramId"] for e in entries):
            await self.notifier.sendUser(telegramId, text)

    def shippingAddress(self, user: dict[str, Any]) -> dict[str, str]:
        """Map the saved profile onto Reap's address fields."""
        first, _, last = user["name"].partition(" ")
        return {
            "firstName": first,
            "lastName": last or first,
            "phone": self.phone,
            "addressLine1": user["addressLine1"],
            "city": user["city"],
            "postalCode": user.get("postalCode", ""),
            "country": user["country"],
        }
