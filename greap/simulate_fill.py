"""Demo helper: fill an open queue as if other shoppers joined and already paid.

Stop the bot first. The bot keeps the queue in memory and rewrites the data file
on every change, so editing while it runs would be lost. Then restart the bot.
Usage: python -m greap.simulate_fill "Box of 6 Mixed Cookies"
"""

import asyncio
import sys
from typing import Any

import httpx

from greap.clock import Clock
from greap.config import loadSettings
from greap.constants import ENTRY_PAID, QUEUE_OPEN
from greap.context_store import ContextStore
from greap.queue_deadlines import lockNotices
from greap.queue_engine import joinQueue

SIMULATED_ID = "sim-1"
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
SIMULATED_PROFILE = {
    "name": "Simulated Shopper",
    "addressLine1": "1 Demo Street",
    "city": "Singapore",
    "postalCode": "000000",
    "country": "SG",
}


def findOpenQueue(store: ContextStore, nameFragment: str) -> dict[str, Any]:
    """Match by name so the command line stays readable."""
    for queue in store.data["queues"].values():
        if (
            queue["status"] == QUEUE_OPEN
            and nameFragment.lower() in queue["name"].lower()
        ):
            return queue
    raise SystemExit(f"No open queue matching '{nameFragment}'.")


def queueAsProduct(queue: dict[str, Any]) -> dict[str, Any]:
    """joinQueue takes a product, so rebuild one from the queue's own fields."""
    keys = ("productId", "variantId", "name", "merchant", "currency")
    product = {key: queue[key] for key in keys}
    return {
        **product,
        "cartonSize": queue["cartonSize"],
        "cartonPrice": queue["cartonPrice"],
    }


async def sendTelegram(token: str, chatId: str, text: str) -> None:
    """Message a real user directly, since this runs outside the bot process."""
    async with httpx.AsyncClient() as http:
        await http.post(
            TELEGRAM_API.format(token=token), json={"chat_id": chatId, "text": text}
        )


async def main(nameFragment: str) -> None:
    """Fill the queue, lock it, and tell the real users to pay."""
    settings = loadSettings()
    store = ContextStore(settings.dataDir)
    queue = findOpenQueue(store, nameFragment)
    missing = queue["cartonSize"] - queue["unitsFilled"]
    store.upsertUser(SIMULATED_ID, **SIMULATED_PROFILE)
    simulated = joinQueue(
        store, SIMULATED_ID, queueAsProduct(queue), missing, Clock().now()
    )
    # Notices are built while entries are still 'locked', before we mark them paid.
    notices = lockNotices(store, queue)
    for entry in simulated:
        entry["status"] = ENTRY_PAID
    store.save()
    size = queue["cartonSize"]
    print(f"{queue['name']} filled to {size}/{size} and locked.")
    for telegramId, text in notices:
        if telegramId == SIMULATED_ID:
            continue
        print(f"[to {telegramId}] {text}")
        if settings.telegramToken:
            await sendTelegram(settings.telegramToken, telegramId, text)


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:])))
