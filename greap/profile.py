"""What counts as a complete profile; Reap needs every field for shipping."""

from typing import Any

# Merchants refuse to quote shipping without a postal code, so it is required.
REQUIRED_PROFILE_FIELDS = ("name", "addressLine1", "city", "postalCode", "country")
PROFILE_FIELDS = REQUIRED_PROFILE_FIELDS


def missingProfileFields(user: dict[str, Any] | None) -> list[str]:
    """Fields still to collect, in the order they should be asked."""
    saved = user or {}
    return [field for field in REQUIRED_PROFILE_FIELDS if not saved.get(field)]
