"""A clock with an adjustable offset so 5-day deadlines can be demoed in seconds."""

from datetime import datetime, timedelta, timezone


class Clock:
    """Wraps 'now' so tests and the CLI demo can move time forward."""

    def __init__(self) -> None:
        # Offset stays zero in production, so the clock is then real time.
        self.offset = timedelta(0)

    def now(self) -> datetime:
        """Current time in UTC, shifted by any demo offset."""
        return datetime.now(timezone.utc) + self.offset

    def advance(self, hours: float) -> None:
        """Jump forward; used by the CLI /advance command."""
        self.offset += timedelta(hours=hours)


def toIso(moment: datetime) -> str:
    """Store timestamps as ISO strings because JSON has no datetime type."""
    return moment.isoformat()


def fromIso(text: str) -> datetime:
    """Inverse of toIso."""
    return datetime.fromisoformat(text)
