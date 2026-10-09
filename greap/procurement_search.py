"""Procurement Agent, search half (FR-7.8, FR-7.9): find, classify, price."""

from typing import Any

from greap.bulk_classifier import BulkClassifier, isBulkEligible
from greap.constants import MODE_DIRECT_ONLY, MODE_QUEUE_OR_DIRECT
from greap.constants import MAX_SEARCH_FETCHES, REAP_FETCH_SIZE
from greap.constants import SEARCH_RESULT_LIMIT
from greap.context_store import ContextStore
from greap.money import unitPriceOf
from greap.reap_client import ReapClient


def stableKeyOf(raw: dict[str, Any]) -> str:
    """Reap issues new product and variant ids on every search, so queues need
    an identity that survives between users' searches: merchant plus name."""
    name = " ".join(raw["name"].lower().split())
    return f"{raw['merchant']['name'].lower()}|{name}"


class ProcurementSearch:
    """Treats Reap plus the LLM as one search API for the rest of the app."""

    def __init__(
        self, reap: ReapClient, classifier: BulkClassifier, store: ContextStore
    ) -> None:
        self.reap = reap
        self.classifier = classifier
        self.store = store

    async def search(self, query: str, cursor: str | None) -> dict[str, Any]:
        """Return one page of priced products plus the cursor for the next."""
        found, nextCursor = await self.collectPage(query, cursor)
        await self.classifier.classifyProducts(found)
        return {
            "products": [self.toProduct(p) for p in found],
            "nextCursor": nextCursor,
        }

    async def collectPage(
        self, query: str, cursor: str | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Keep fetching until all sellable products (up to the cap) are gathered.

        Reap filters out unavailable items after paging, so one fetch can hold
        far fewer than the limit even when many more results exist.
        """
        found: list[dict[str, Any]] = []
        for _ in range(MAX_SEARCH_FETCHES):
            # Never ask for more than the cap still allows, so we cannot overshoot.
            wanted = min(REAP_FETCH_SIZE, SEARCH_RESULT_LIMIT - len(found))
            page = await self.reap.searchProducts(query, wanted, cursor)
            found += [p for p in page["products"] if self.isSellable(p)]
            pagination = page.get("pagination", {})
            cursor = (
                pagination.get("nextCursor") if pagination.get("hasNextPage") else None
            )
            if len(found) >= SEARCH_RESULT_LIMIT or not cursor:
                break
        for product in found:
            product["stableKey"] = stableKeyOf(product)
        return found, cursor

    def isSellable(self, raw: dict[str, Any]) -> bool:
        """The preview variant is what we would buy, so it must exist."""
        return bool(raw.get("available") and raw.get("previewVariant"))

    def toProduct(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten Reap's shape into what queues and the agent need."""
        classification = self.store.getClassification(raw["stableKey"])
        eligible = isBulkEligible(classification)
        price = raw["previewVariant"]["price"]
        cartonSize = int(classification["unitsPerBulk"]) if eligible else 1
        return {
            "productId": raw["stableKey"],
            "variantId": raw["previewVariant"]["id"],
            "name": raw["name"],
            "merchant": raw["merchant"]["name"],
            "currency": price["currency"],
            "cartonPrice": price["amount"],
            "cartonSize": cartonSize,
            "unitLabel": (
                classification.get("unitLabel", "unit") if eligible else "item"
            ),
            "unitPrice": unitPriceOf(price["amount"], cartonSize),
            "mode": MODE_QUEUE_OR_DIRECT if eligible else MODE_DIRECT_ONLY,
        }

    async def resolveVariantId(self, queue: dict[str, Any]) -> str | None:
        """Get a fresh Reap variant id at order time, since stored ones go stale."""
        page = await self.search(queue["name"], None)
        for product in page["products"]:
            if product["productId"] == queue["productId"]:
                return product["variantId"]
        return None
