"""Named constants shared across Greap so no magic numbers live in the logic."""

# Business rules from the PRD (sections 3 to 6)
QUEUE_DEADLINE_DAYS = 5
PAYMENT_WINDOW_HOURS = 24
# Show everything Reap returns, up to a cap so a broad query cannot run away.
SEARCH_RESULT_LIMIT = 50
REAP_FETCH_SIZE = 20
MAX_SEARCH_FETCHES = 10
TELEGRAM_MESSAGE_LIMIT = 4000
LOW_CONFIDENCE_THRESHOLD = 0.7
MONEY_DECIMALS = 2

# Entry lifecycle (PRD order record "status")
ENTRY_QUEUED = "queued"
ENTRY_LOCKED = "locked"
ENTRY_PAID = "paid"
ENTRY_ORDERED = "ordered"
ENTRY_CANCELLED = "cancelled"
ENTRY_EXPIRED = "expired"

# Queue lifecycle. "short" means the deadline passed before the carton filled.
QUEUE_OPEN = "open"
QUEUE_SHORT = "short"
QUEUE_LOCKED = "locked"
QUEUE_ORDERING = "ordering"
QUEUE_ORDERED = "ordered"
QUEUE_CLOSED = "closed"

# Entry types (PRD order record "type")
TYPE_QUEUE = "queue"
TYPE_DIRECT = "direct"

# Choices offered to users when a queue misses its deadline (FR-6.2)
CHOICE_BUY_REMAINING = "buy_remaining"
CHOICE_EXTEND = "extend"
CHOICE_CANCEL = "cancel"

# Product purchase modes shown to the user (FR-2.5)
MODE_QUEUE_OR_DIRECT = "queue_or_direct"
MODE_DIRECT_ONLY = "direct_only"

# Reap Agentic API
REAP_VERSION = "2025-02-14"
REAP_SIMULATE_HEADER = "X-Simulate-Checkout"
REAP_SIMULATE_COMPLETED = "COMPLETED"
REAP_STATUS_ACTIVE = "ACTIVE"
REAP_STATUS_COMPLETED = "COMPLETED"
REAP_STATUS_REQUIRES_ACTION = "REQUIRES_ACTION"
REAP_TERMINAL_BAD_STATUSES = ("FAILED", "REVOKED", "EXPIRED", "CANCELLED")
REAP_RETURN_URL = "https://example.com/done"
REAP_POLL_SECONDS = 3
REAP_POLL_ATTEMPTS = 200
REAP_AVAILABILITY_FILTER = "AVAILABLE_ONLY"

# Agent behaviour
MAX_TOOL_ROUNDS = 8
MAX_HISTORY_MESSAGES = 30
TICK_SECONDS = 60
