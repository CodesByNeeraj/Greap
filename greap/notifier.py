"""How the core app reaches people, kept abstract so Telegram and CLI both fit."""

from typing import Protocol


class Notifier(Protocol):
    """Anything that can message a user or the operator."""

    async def sendUser(self, telegramId: str, text: str) -> None:
        """Send a proactive message (queue locked, deadline passed, order placed)."""

    async def sendOps(self, text: str) -> None:
        """Send the operator links that need a human, e.g. Reap approval pages."""
