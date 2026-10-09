"""Thin async client for Reap's Agentic API: one method per endpoint we use."""

import uuid
from typing import Any

import httpx

from greap.config import Settings
from greap.constants import REAP_AVAILABILITY_FILTER, REAP_RETURN_URL
from greap.constants import REAP_SIMULATE_COMPLETED, REAP_SIMULATE_HEADER

REQUEST_TIMEOUT_SECONDS = 30


class ReapApiError(RuntimeError):
    """Raised for non-2xx replies so callers can show Reap's own reason."""


class ReapClient:
    """Keeps auth headers, versioning and idempotency in one place."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.AsyncClient(
            base_url=settings.reapBaseUrl, timeout=REQUEST_TIMEOUT_SECONDS
        )

    async def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        extraHeaders: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send one call; POSTs get a fresh idempotency key to be retry-safe."""
        headers = {
            "Authorization": f"Bearer {self.settings.reapApiKey}",
            "Reap-Version": self.settings.reapVersion,
            **(extraHeaders or {}),
        }
        if method == "POST":
            headers["Idempotency-Key"] = str(uuid.uuid4())
        reply = await self.http.request(method, path, json=body, headers=headers)
        if reply.status_code >= 400:
            raise ReapApiError(f"{method} {path} -> {reply.status_code}: {reply.text}")
        return reply.json()

    async def searchProducts(self, query: str, limit: int, cursor: str | None) -> dict:
        """Search Reap's merchant catalog; available items only (FR-2.3)."""
        pagination: dict[str, Any] = {"limit": limit}
        if cursor:
            pagination["cursor"] = cursor
        return await self.request(
            "POST",
            "/agentic/products/search",
            {
                "query": query,
                "context": {
                    "country": self.settings.reapCountry,
                    "currency": self.settings.reapCurrency,
                },
                "filters": {"availability": REAP_AVAILABILITY_FILTER},
                "pagination": pagination,
            },
        )

    async def createEnrollment(self, customerId: str) -> dict:
        """Start hosted card capture; the card never touches our servers."""
        return await self.request(
            "POST",
            "/agentic/enrollments",
            {
                "source": "EXTERNAL",
                "owner": {
                    "type": "CLIENT_REFERENCE",
                    "id": customerId,
                    "email": self.settings.orderEmail,
                },
                "presentation": {"type": "REDIRECT", "returnUrl": REAP_RETURN_URL},
            },
        )

    async def getEnrollment(self, enrollmentId: str) -> dict:
        """Used to confirm the card is ACTIVE before charging."""
        return await self.request("GET", f"/agentic/enrollments/{enrollmentId}")

    async def createQuote(self, variantId: str, quantity: int, address: dict) -> dict:
        """Price one purchase line; Reap needs the address for shipping and tax."""
        return await self.request(
            "POST",
            "/agentic/quotes",
            {
                "items": [{"variantId": variantId, "quantity": quantity}],
                "email": self.settings.orderEmail,
                "shippingAddress": address,
            },
        )

    async def createCheckout(self, quoteId: str, enrollmentId: str) -> dict:
        """Charge the enrolled card. The sandbox header simulates a success."""
        return await self.request(
            "POST",
            "/agentic/checkouts",
            {
                "quoteId": quoteId,
                "enrollmentId": enrollmentId,
                "presentation": {"type": "REDIRECT", "returnUrl": REAP_RETURN_URL},
            },
            {REAP_SIMULATE_HEADER: REAP_SIMULATE_COMPLETED},
        )

    async def getCheckout(self, checkoutId: str) -> dict:
        """Poll for the merchant order id after the user approves."""
        return await self.request("GET", f"/agentic/checkouts/{checkoutId}")
