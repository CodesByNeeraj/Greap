"""Shared fixtures: a fresh store and the PRD's Golden Oreo product."""

from datetime import datetime, timezone

import pytest

from greap.context_store import ContextStore


@pytest.fixture
def store(tmp_path):
    """Empty store in a temp folder so tests never touch real data."""
    return ContextStore(tmp_path)


@pytest.fixture
def now():
    """A fixed moment so deadline maths is deterministic."""
    return datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def oreo():
    """PRD example: 24/carton at SGD 132, so SGD 5.50 per unit."""
    return {
        "productId": "prd_oreo",
        "variantId": "var_oreo",
        "name": "Golden Oreo 133g",
        "merchant": "Tasty Snack Asia",
        "currency": "SGD",
        "cartonSize": 24,
        "cartonPrice": 132.0,
    }
