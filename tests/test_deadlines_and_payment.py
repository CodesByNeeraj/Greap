"""Sad flow, unpaid expiry and the exact-amount payment rule."""

from datetime import timedelta

from greap.payment_desk import PaymentDesk
from greap.queue_deadlines import applyChoice, expireUnpaid, markShortQueues
from greap.queue_engine import joinQueue


def test_short_queue_offers_choices_at_deadline(store, now, oreo):
    joinQueue(store, "A", oreo, 18, now)
    assert markShortQueues(store, now + timedelta(days=1)) == []
    notices = markShortQueues(store, now + timedelta(days=5, minutes=1))
    assert "18/24" in notices[0][1] and "remaining 6" in notices[0][1]


def test_buy_remaining_locks_queue(store, now, oreo):
    entry = joinQueue(store, "A", oreo, 18, now)[0]
    later = now + timedelta(days=6)
    markShortQueues(store, later)
    applyChoice(store, entry, "buy_remaining", later)
    assert entry["units"] == 24 and entry["status"] == "locked"


def test_everyone_cancelling_closes_queue(store, now, oreo):
    entry = joinQueue(store, "A", oreo, 18, now)[0]
    later = now + timedelta(days=6)
    markShortQueues(store, later)
    applyChoice(store, entry, "cancel", later)
    assert store.getQueue(entry["queueId"])["status"] == "closed"


def test_extend_reopens_with_new_deadline(store, now, oreo):
    entry = joinQueue(store, "A", oreo, 18, now)[0]
    later = now + timedelta(days=6)
    markShortQueues(store, later)
    applyChoice(store, entry, "extend", later)
    queue = store.getQueue(entry["queueId"])
    assert queue["status"] == "open" and queue["deadline"] > later.isoformat()


def test_unpaid_entries_expire_and_queue_reopens(store, now, oreo):
    joinQueue(store, "A", oreo, 10, now)
    paid = joinQueue(store, "B", oreo, 14, now)[0]
    paid["status"] = "paid"
    expireUnpaid(store, now + timedelta(hours=23))
    assert store.entriesForUser("A")[0]["status"] == "locked"
    expireUnpaid(store, now + timedelta(hours=25))
    assert store.entriesForUser("A")[0]["status"] == "expired"
    queue = store.getQueue(paid["queueId"])
    assert queue["status"] == "open" and queue["unitsFilled"] == 14


def test_payment_requires_exact_amount(store, now, oreo):
    joinQueue(store, "A", oreo, 24, now)
    desk = PaymentDesk(store)
    assert "exact amount" in desk.startPayment("A")
    for wrong in ("100", "131.99", "132.01", "abc"):
        reply, paid = desk.handleAmount("A", wrong)
        assert paid is None and "not the amount due" in reply
    reply, paid = desk.handleAmount("A", "SGD 132.00")
    assert paid["status"] == "paid" and not desk.isPaying("A")


def test_nothing_to_pay(store):
    assert "nothing to pay" in PaymentDesk(store).startPayment("A")
