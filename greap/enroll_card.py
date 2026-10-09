"""One-time card setup: run before the demo so orders never wait on a card page."""

import asyncio
import subprocess

from greap.cli_chat import ConsoleNotifier
from greap.config import loadSettings
from greap.procurement_order import ProcurementOrder
from greap.reap_client import ReapClient

URL_PREFIX = "https://"


class BrowserNotifier(ConsoleNotifier):
    """Prints the link and opens it, since this script has one job."""

    async def sendOps(self, text: str) -> None:
        """Open the first link in the message in the default browser (macOS)."""
        await super().sendOps(text)
        link = next(w for w in text.split() if w.startswith(URL_PREFIX))
        subprocess.run(["open", link], check=False)


async def main() -> None:
    """Reuse the saved enrollment if it is still active, else create one."""
    settings = loadSettings()
    # Search is never used here, so None is safe and avoids loading the LLM stack.
    order = ProcurementOrder(ReapClient(settings), settings, BrowserNotifier(), None)
    enrollmentId = await order.ensureEnrollment()
    print(f"Card enrolled and ready. Enrollment id: {enrollmentId}")


if __name__ == "__main__":
    asyncio.run(main())
