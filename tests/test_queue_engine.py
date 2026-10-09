"""Queue rules from PRD sections 3 and 4, using the PRD's own examples."""

from greap.queue_engine import buyDirect, cancelEntry, changeUnits, joinQueue
from greap.queue_engine import splitUnits


def test_split_units_spills_overflow_into_next_carton():
    assert splitUnits(6, 24, 10) == [6, 4]


def test_split_units_can_span_several_cartons():
    assert splitUnits(6, 24, 60) == [6, 24, 24, 6]


def test_prd_example_three_users_fill_one_carton(store, now, oreo):
    for tid, units in (("A", 10), ("B", 8), ("C", 6)):
        joinQueue(store, tid, oreo, units, now)
    totals = {tid: store.entriesForUser(tid)[0]["total"] for tid in "ABC"}
    assert totals == {"A": 55.0, "B": 44.0, "C": 33.0}
    queue = next(iter(store.data["queues"].values()))
    assert queue["status"] == "locked" and queue["unitsFilled"] == 24


def test_overflow_example_starts_second_carton(store, now, oreo):
    joinQueue(store, "A", oreo, 18, now)
    entries = joinQueue(store, "B", oreo, 10, now)
    assert [e["units"] for e in entries] == [6, 4]
    second = store.openQueueFor("prd_oreo")
    assert second["unitsFilled"] == 4


def test_queue_never_exceeds_carton_size(store, now, oreo):
    joinQueue(store, "A", oreo, 50, now)
    assert all(q["unitsFilled"] <= 24 for q in store.data["queues"].values())


def test_cancel_only_while_queued(store, now, oreo):
    entry = joinQueue(store, "A", oreo, 5, now)[0]
    assert cancelEntry(store, entry["id"], "B") != ""
    assert cancelEntry(store, entry["id"], "A") == ""
    assert store.getQueue(entry["queueId"])["status"] == "closed"


def test_locked_entry_cannot_be_cancelled(store, now, oreo):
    entry = joinQueue(store, "A", oreo, 24, now)[0]
    assert "cannot be cancelled" in cancelEntry(store, entry["id"], "A")


def test_change_units_cannot_overfill(store, now, oreo):
    entry = joinQueue(store, "A", oreo, 20, now)[0]
    joinQueue(store, "B", oreo, 2, now)
    assert "overfill" in changeUnits(store, entry["id"], "A", 23)
    assert changeUnits(store, entry["id"], "A", 22) == ""


def test_direct_purchase_is_locked_at_carton_price(store, now, oreo):
    entry = buyDirect(store, "A", oreo, 2, now)
    assert entry["status"] == "locked" and entry["total"] == 264.0
