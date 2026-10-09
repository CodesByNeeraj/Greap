"""Agent tools for finding and committing to purchases (sections 2 and 3)."""

from datetime import timedelta

from greap.clock import Clock, fromIso, toIso
from greap.constants import MODE_DIRECT_ONLY, QUEUE_DEADLINE_DAYS
from greap.context_store import ContextStore
from greap.money import formatMoney, lineTotal
from greap.notifier import Notifier
from greap.procurement_search import ProcurementSearch
from greap.queue_deadlines import lockNotices
from greap.queue_engine import buyDirect, freeSpaceFor, joinQueue, splitUnits
from greap.queue_pricing import applyPriceChange


class ShoppingTools:
    """Search, join and buy. Remembers the last search per user."""

    def __init__(
        self,
        store: ContextStore,
        search: ProcurementSearch,
        clock: Clock,
        notifier: Notifier,
    ) -> None:
        self.store = store
        self.search = search
        self.clock = clock
        self.notifier = notifier
        self.lastSearch: dict[str, dict[str, dict]] = {}

    async def searchProducts(
        self, tid: str, query: str, cursor: str | None = None
    ) -> dict:
        """FR-2.2 to FR-2.9: one page of results the user can act on."""
        page = await self.search.search(query, cursor)
        self.lastSearch[tid] = {p["productId"]: p for p in page["products"]}
        if not page["products"]:
            return {"products": [], "message": "Nothing found. Ask for another search."}
        await self.refreshPrices(page["products"])
        shown = [self.describe(p) for p in page["products"]]
        fullest = max(shown, key=lambda s: s["fillRatio"])
        fullest["closestToFull"] = fullest["fillRatio"] > 0
        return {"products": shown, "nextCursor": page["nextCursor"]}

    async def refreshPrices(self, products: list[dict]) -> None:
        """FR-4.7: reprice any open queue whose Reap price moved."""
        for product in products:
            queue = self.store.openQueueFor(product["productId"])
            if queue:
                for tid, text in applyPriceChange(
                    self.store, queue, product["cartonPrice"]
                ):
                    await self.notifier.sendUser(tid, text)

    def describe(self, product: dict) -> dict:
        """The fields the agent shows for one result (FR-2.6, FR-2.7)."""
        queue = self.store.openQueueFor(product["productId"])
        filled = queue["unitsFilled"] if queue else 0
        size = product["cartonSize"]
        direct = product["mode"] == MODE_DIRECT_ONLY
        return {
            "productId": product["productId"],
            "name": product["name"],
            "merchant": product["merchant"],
            "mode": product["mode"],
            "cartonPrice": formatMoney(product["cartonPrice"], product["currency"]),
            "unitsPerCarton": size,
            "unitLabel": product["unitLabel"],
            "unitPrice": formatMoney(product["unitPrice"], product["currency"]),
            "queueProgress": None if direct else f"{filled}/{size} filled",
            "fillRatio": 0 if direct else filled / size,
        }

    def preview(self, product: dict, units: int) -> dict:
        """FR-3.5: everything the user confirms before anything is saved."""
        queue = self.store.openQueueFor(product["productId"])
        space = freeSpaceFor(self.store, product)
        chunks = splitUnits(space, product["cartonSize"], units)
        deadline = (
            fromIso(queue["deadline"])
            if queue
            else self.clock.now() + timedelta(days=QUEUE_DEADLINE_DAYS)
        )
        return {
            "needsConfirmation": True,
            "product": product["name"],
            "units": units,
            "unitPrice": formatMoney(product["unitPrice"], product["currency"]),
            "total": formatMoney(
                lineTotal(product["unitPrice"], units), product["currency"]
            ),
            "deadline": toIso(deadline),
            "unitsSpillingIntoNextCarton": sum(chunks[1:]),
            "instruction": (
                "Show this, ask the user to confirm, "
                "then call again with confirmed=true."
            ),
        }

    def lookup(self, tid: str, productId: str) -> dict | None:
        """Only products from the user's latest search can be bought."""
        return self.lastSearch.get(tid, {}).get(productId)

    async def joinQueueTool(
        self, tid: str, productId: str, units: int, confirmed: bool
    ) -> dict:
        """FR-3.3 to FR-3.9: join, with a two-step confirmation."""
        product = self.lookup(tid, productId)
        if not product or product["mode"] == MODE_DIRECT_ONLY or units < 1:
            return {"error": "Search first, pick a bulk product and give units >= 1."}
        if not confirmed:
            return self.preview(product, units)
        entries = joinQueue(self.store, tid, product, units, self.clock.now())
        queue = self.store.getQueue(entries[0]["queueId"])
        await self.announceLocks(tid, entries)
        return {
            "joined": [
                {"entryId": e["id"], "units": e["units"], "status": e["status"]}
                for e in entries
            ],
            "queueProgress": f"{queue['unitsFilled']}/{queue['cartonSize']}",
            "fullAndLocked": any(e["status"] == "locked" for e in entries),
        }

    async def announceLocks(self, tid: str, entries: list[dict]) -> None:
        """FR-5.1: message the other users of any queue this join just filled."""
        for queueId in dict.fromkeys(e["queueId"] for e in entries):
            for who, text in lockNotices(self.store, self.store.getQueue(queueId)):
                if who != tid:
                    await self.notifier.sendUser(who, text)

    async def buyCartonTool(
        self, tid: str, productId: str, cartons: int, confirmed: bool
    ) -> dict:
        """FR-3.7: whole cartons at carton price, then straight to payment."""
        product = self.lookup(tid, productId)
        if not product or cartons < 1:
            return {"error": "Search first and give cartons >= 1."}
        total = formatMoney(product["cartonPrice"] * cartons, product["currency"])
        if not confirmed:
            return {
                "needsConfirmation": True,
                "product": product["name"],
                "cartons": cartons,
                "total": total,
            }
        entry = buyDirect(self.store, tid, product, cartons, self.clock.now())
        return {
            "entryId": entry["id"],
            "total": total,
            "next": "Tell the user to use /pay now.",
        }
