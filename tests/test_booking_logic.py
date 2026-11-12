from datetime import datetime
from app.booking_logic import overlaps, find_conflicts

def dt(hour, minute=0):
    return datetime(2026, 12, 1, hour, minute)

def test_back_to_back_does_not_overlap():
    assert overlaps(dt(10), dt(11), dt(11), dt(12)) is False

def test_partial_overlap():
    assert overlaps(dt(10), dt(11), dt(10, 30), dt(11, 30)) is True

def test_contained_overlap():
    assert overlaps(dt(9), dt(12), dt(10), dt(11)) is True

def test_identical_ranges():
    assert overlaps(dt(10), dt(11), dt(10), dt(11)) is True

def test_disjoint():
    assert overlaps(dt(8), dt(9), dt(10), dt(11)) is False
def make_booking(booking_id, start, end, status="confirmed"):
    return {"id": booking_id, "start": start, "end": end, "status": status}


def test_find_conflicts_returns_overlapping_booking():
    existing = [make_booking("b1", dt(10), dt(11))]
    conflicts = find_conflicts(dt(10, 30), dt(11, 30), existing)
    assert [b["id"] for b in conflicts] == ["b1"]


def test_find_conflicts_ignores_back_to_back():
    existing = [make_booking("b1", dt(10), dt(11))]
    assert find_conflicts(dt(11), dt(12), existing) == []


def test_find_conflicts_ignores_cancelled():
    existing = [make_booking("b1", dt(10), dt(11), status="cancelled")]
    assert find_conflicts(dt(10), dt(11), existing) == []


def test_find_conflicts_empty_list():
    assert find_conflicts(dt(10), dt(11), []) == []