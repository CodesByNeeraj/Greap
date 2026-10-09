"""The /pay flow: the user must type the exact amount due (FR-5.3 to FR-5.5)."""

from decimal import Decimal
from typing import Any

from greap.constants import ENTRY_LOCKED, ENTRY_PAID
from greap.context_store import ContextStore
from greap.money import formatMoney, parseAmount, toDecimal

CANCEL_WORDS = ("cancel", "/cancel", "stop")


class PaymentDesk:
    """Remembers which entry each user is in the middle of paying."""

    def __init__(self, store: ContextStore) -> None:
        self.store = store
        self.pending: dict[str, str] = {}

    def isPaying(self, telegramId: str) -> bool:
        """The app routes the next message here while this is true."""
        return telegramId in self.pending

    def startPayment(self, telegramId: str) -> str:
        """Pick the oldest unpaid locked entry and ask for the exact amount."""
        due = [
            e
            for e in self.store.entriesForUser(telegramId)
            if e["status"] == ENTRY_LOCKED
        ]
        if not due:
            return "You have nothing to pay right now."
        entry = due[0]
        self.pending[telegramId] = entry["id"]
        queue = self.store.getQueue(entry["queueId"])
        return (
            f"{queue['name']}: {entry['units']} units. Type the exact amount due "
            f"({formatMoney(entry['total'], queue['currency'])}) to pay, "
            "or 'cancel' to stop."
        )

    def handleAmount(
        self, telegramId: str, text: str
    ) -> tuple[str, dict[str, Any] | None]:
        """Accept only the exact amount; anything else is rejected (FR-5.5)."""
        if text.strip().lower() in CANCEL_WORDS:
            del self.pending[telegramId]
            return "Payment cancelled. Use /pay when you are ready.", None
        entry = self.store.getEntry(self.pending[telegramId])
        queue = self.store.getQueue(entry["queueId"])
        typed = parseAmount(text)
        if typed is None or not self.isExact(typed, entry["total"]):
            return (
                f"That is not the amount due. Please type exactly "
                f"{formatMoney(entry['total'], queue['currency'])}.",
                None,
            )
        del self.pending[telegramId]
        entry["status"] = ENTRY_PAID
        self.store.save()
        return f"Payment received for {queue['name']}. Thank you!", entry

    def isExact(self, typed: Decimal, due: float) -> bool:
        """Below or above the amount due both fail."""
        return typed == toDecimal(due)
