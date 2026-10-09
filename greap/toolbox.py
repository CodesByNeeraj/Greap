"""Dispatches agent tool calls to the right module (FR-1, FR-8, section 6)."""

from typing import Any

import httpx

from greap.clock import Clock
from greap.constants import ENTRY_CANCELLED, ENTRY_EXPIRED, ENTRY_ORDERED, ENTRY_PAID
from greap.context_store import ContextStore
from greap.money import formatMoney
from greap.notifier import Notifier
from greap.procurement_search import ProcurementSearch
from greap.profile import PROFILE_FIELDS, missingProfileFields
from greap.queue_deadlines import applyChoice
from greap.reap_client import ReapApiError
from greap.queue_engine import cancelEntry, changeUnits
from greap.recommendations import recommendationsFor
from greap.shopping_tools import ShoppingTools

# Onboarding comes first: nothing works until the profile is complete.
NEEDS_PROFILE = ("search_products", "join_queue", "buy_carton")


class Toolbox:
    """One entry point, run(), so the agent loop stays tiny."""

    def __init__(
        self,
        store: ContextStore,
        search: ProcurementSearch,
        clock: Clock,
        notifier: Notifier,
    ) -> None:
        self.store = store
        self.clock = clock
        self.notifier = notifier
        self.shopping = ShoppingTools(store, search, clock, notifier)

    async def run(self, tid: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Run a tool by name; unknown names return an error the model can read."""
        handlers = {
            "save_profile": self.saveProfile,
            "search_products": self.shopping.searchProducts,
            "join_queue": self.shopping.joinQueueTool,
            "buy_carton": self.shopping.buyCartonTool,
            "get_status": self.getStatus,
            "change_units": self.changeUnitsTool,
            "cancel_entry": self.cancelEntryTool,
            "resolve_short_queue": self.resolveShortQueue,
            "get_past_purchases": self.getPastPurchases,
            "get_recommendations": self.getRecommendations,
        }
        if name not in handlers:
            return {"error": f"Unknown tool {name}"}
        missing = missingProfileFields(self.store.getUser(tid))
        if name in NEEDS_PROFILE and missing:
            # Orders need a full address, so block shopping until it is saved.
            return {"error": f"Profile incomplete. Ask the user for: {missing}"}
        try:
            return await handlers[name](tid, **args)
        except TypeError as error:
            return {"error": f"Bad arguments: {error}"}
        except (ReapApiError, httpx.TransportError) as error:
            # Reap outages happen; the agent should tell the user, not go silent.
            return {"error": f"Reap is unavailable right now, try again soon: {error}"}

    async def saveProfile(self, tid: str, **fields: str) -> dict:
        """FR-1.4 and FR-1.6: partial saves let onboarding go one question at a time."""
        user = self.store.upsertUser(
            tid, **{k: v for k, v in fields.items() if k in PROFILE_FIELDS}
        )
        return {
            "saved": True,
            "stillMissing": missingProfileFields(user),
        }

    def describeEntry(self, entry: dict) -> dict:
        """FR-8.1: product, units, progress, status and deadline."""
        queue = self.store.getQueue(entry["queueId"])
        return {
            "entryId": entry["id"],
            "product": queue["name"],
            "units": entry["units"],
            "total": formatMoney(entry["total"], queue["currency"]),
            "queueProgress": f"{queue['unitsFilled']}/{queue['cartonSize']}",
            "status": entry["status"],
            "queueStatus": queue["status"],
            "deadline": queue["deadline"],
        }

    async def getStatus(self, tid: str) -> dict:
        """Live entries only; finished ones are in past purchases."""
        done = (ENTRY_CANCELLED, ENTRY_EXPIRED, ENTRY_PAID, ENTRY_ORDERED)
        return {
            "entries": [
                self.describeEntry(e)
                for e in self.store.entriesForUser(tid)
                if e["status"] not in done
            ]
        }

    async def changeUnitsTool(self, tid: str, entryId: str, units: int) -> dict:
        """FR-8.2."""
        error = changeUnits(self.store, entryId, tid, units)
        return (
            {"error": error}
            if error
            else self.describeEntry(self.store.getEntry(entryId))
        )

    async def cancelEntryTool(self, tid: str, entryId: str) -> dict:
        """FR-8.3."""
        error = cancelEntry(self.store, entryId, tid)
        return {"error": error} if error else {"cancelled": entryId}

    async def resolveShortQueue(self, tid: str, entryId: str, choice: str) -> dict:
        """FR-6.2 to FR-6.5: apply the choice and tell the other users."""
        entry = self.store.getEntry(entryId)
        if not entry or entry["telegramId"] != tid:
            return {"error": "No such entry for this user."}
        for who, text in applyChoice(self.store, entry, choice, self.clock.now()):
            if who != tid:
                await self.notifier.sendUser(who, text)
        return self.describeEntry(entry)

    async def getPastPurchases(self, tid: str) -> dict:
        """FR-8.4."""
        done = (ENTRY_PAID, ENTRY_ORDERED)
        return {
            "purchases": [
                self.describeEntry(e)
                for e in self.store.entriesForUser(tid)
                if e["status"] in done
            ]
        }

    async def getRecommendations(self, tid: str) -> dict:
        """FR-7.3 and FR-7.4."""
        return {"recommendations": recommendationsFor(self.store, tid)}
