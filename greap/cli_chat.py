"""Terminal chat for testing without Telegram.

Commands: /as <id> switches user, /advance <hours> moves the clock, /tick runs
the deadline checks.
"""

import asyncio

from greap.config import loadSettings
from greap.greap_app import GreapApp

DEFAULT_USER = "1001"


class ConsoleNotifier:
    """Prints proactive messages so they are visible in the terminal."""

    async def sendUser(self, telegramId: str, text: str) -> None:
        """Show who the message is for."""
        print(f"  [to {telegramId}] {text}")

    async def sendOps(self, text: str) -> None:
        """Show operator links, e.g. the Reap approval page."""
        print(f"  [OPS] {text}")


async def handleCommand(app: GreapApp, line: str, user: str) -> str | None:
    """Return the new user id for /as, else run the command and return None."""
    command, _, argument = line.partition(" ")
    if command == "/as":
        return argument.strip() or user
    if command == "/advance":
        app.clock.advance(float(argument))
    await app.tick()
    return None


async def main() -> None:
    """Read lines from the terminal forever."""
    app = GreapApp(loadSettings(), ConsoleNotifier())
    user = DEFAULT_USER
    print("Greap CLI. /as <id>, /advance <hours>, /tick, /pay, Ctrl-C to quit.")
    while True:
        line = (await asyncio.to_thread(input, f"{user}> ")).strip()
        if line.split(" ")[0] in ("/as", "/advance", "/tick"):
            user = await handleCommand(app, line, user) or user
            continue
        for reply in await app.handleMessage(user, line):
            print(f"bot> {reply}")


if __name__ == "__main__":
    asyncio.run(main())
