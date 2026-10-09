"""Procurement Agent, order half (FR-7.11, FR-7.12): quote, charge, confirm."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from greap.config import Settings
from greap.constants import REAP_POLL_ATTEMPTS, REAP_POLL_SECONDS
from greap.constants import REAP_STATUS_ACTIVE, REAP_STATUS_COMPLETED
from greap.constants import REAP_STATUS_REQUIRES_ACTION, REAP_TERMINAL_BAD_STATUSES
from greap.notifier import Notifier
from greap.procurement_search import ProcurementSearch
from greap.reap_client import ReapApiError, ReapClient

ENROLLMENT_FILE_NAME = "reap-enrollment.json"
ENROLLMENT_CUSTOMER_ID = "greap-buying-account"


@dataclass
class OrderResult:
    """What the Orchestrator needs to tell users about an order."""

    success: bool
    orderId: str = ""
    amount: str = ""
    error: str = ""


class ProcurementOrder:
    """Places one Reap order per filled queue or direct purchase."""

    def __init__(
        self,
        reap: ReapClient,
        settings: Settings,
        notifier: Notifier,
        search: ProcurementSearch,
    ) -> None:
        self.search = search
        self.reap = reap
        self.settings = settings
        self.notifier = notifier
        self.enrollmentPath = settings.dataDir / ENROLLMENT_FILE_NAME

    async def placeOrder(
        self, queue: dict[str, Any], address: dict[str, str]
    ) -> OrderResult:
        """Quote then check out; any Reap rejection becomes a readable failure."""
        try:
            # Stored variant ids go stale, so fetch a live one for this order.
            variantId = await self.search.resolveVariantId(queue)
            if not variantId:
                return OrderResult(False, error="Product no longer in Reap catalog")
            enrollmentId = await self.ensureEnrollment()
            quote = await self.reap.createQuote(variantId, queue["cartons"], address)
            checkout = await self.reap.createCheckout(quote["id"], enrollmentId)
            return await self.waitForCheckout(checkout)
        except (ReapApiError, TimeoutError) as error:
            return OrderResult(success=False, error=str(error))

    async def ensureEnrollment(self) -> str:
        """One company card is enrolled once, then reused for every order."""
        if self.enrollmentPath.exists():
            saved = json.loads(self.enrollmentPath.read_text())["id"]
            current = await self.reap.getEnrollment(saved)
            if current["status"] == REAP_STATUS_ACTIVE:
                return saved
        enrollment = await self.reap.createEnrollment(ENROLLMENT_CUSTOMER_ID)
        self.settings.dataDir.mkdir(parents=True, exist_ok=True)
        self.enrollmentPath.write_text(json.dumps({"id": enrollment["id"]}))
        await self.notifier.sendOps(
            "Card needed once for Reap. Open and enter the sandbox card "
            f"(OTP 456789):\n{enrollment['nextAction']['url']}"
        )
        await self.pollUntil(lambda: self.enrollmentActive(enrollment["id"]))
        return enrollment["id"]

    async def enrollmentActive(self, enrollmentId: str) -> bool:
        """True once the hosted card page was completed."""
        status = (await self.reap.getEnrollment(enrollmentId))["status"]
        if status in REAP_TERMINAL_BAD_STATUSES:
            raise ReapApiError(f"Enrollment ended as {status}")
        return status == REAP_STATUS_ACTIVE

    async def waitForCheckout(self, checkout: dict[str, Any]) -> OrderResult:
        """The human approves on Reap's hosted page, so poll until it finishes."""
        if checkout.get("nextAction"):
            await self.notifier.sendOps(
                f"Approve this purchase on Reap:\n{checkout['nextAction']['url']}"
            )
        final = await self.pollUntil(lambda: self.checkoutDone(checkout["id"]))
        return OrderResult(
            success=True,
            orderId=final.get("orderId", ""),
            amount=str(final.get("finalAmount", {}).get("amount", "")),
        )

    async def checkoutDone(self, checkoutId: str) -> dict[str, Any] | bool:
        """Return the final checkout once it is no longer waiting for approval."""
        current = await self.reap.getCheckout(checkoutId)
        if current["status"] == REAP_STATUS_COMPLETED:
            return current
        if current["status"] != REAP_STATUS_REQUIRES_ACTION:
            raise ReapApiError(f"Checkout ended as {current['status']}")
        return False

    async def pollUntil(self, check: Any) -> Any:
        """Poll a coroutine function until it returns something truthy."""
        for _ in range(REAP_POLL_ATTEMPTS):
            result = await check()
            if result:
                return result
            await asyncio.sleep(REAP_POLL_SECONDS)
        raise TimeoutError("Timed out waiting for Reap.")
