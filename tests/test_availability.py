from twojtenis_mcp.availability import (
    SLOT_MINUTES,
    _interval_overlap,
    _slots_for_window,
    build_availability,
)


def test_slot_window_30_min():
    slots = _slots_for_window(7 * 60, 9 * 60)
    assert slots == [(420, 450), (450, 480), (480, 510), (510, 540)]
    assert SLOT_MINUTES == 30


def test_slot_window_drops_partial_tail():
    # 07:00 to 07:25 — no full 30-min slot fits
    assert _slots_for_window(420, 445) == []


def test_overlap_detection():
    assert _interval_overlap(60, 90, 75, 120) is True
    assert _interval_overlap(60, 90, 90, 120) is False  # touch, no overlap
    assert _interval_overlap(60, 90, 0, 60) is False
    assert _interval_overlap(60, 90, 0, 200) is True


def test_build_availability_marks_booked_slots_unavailable():
    locations = [
        {
            "id": "loc-1",
            "name": "Court 1",
            "type": 0,
            "tags": "Tennis",
            "isEnabled": True,
        }
    ]
    open_hours = {"monday": {"from": "09:00:00", "to": "11:00:00"}}
    # 2026-05-11 is a Monday
    bookings = [
        {
            "locationId": "loc-1",
            "startTime": "10:00:00",
            "endTime": "10:30:00",
        }
    ]
    grid = build_availability(
        iso_date="2026-05-11",
        locations=locations,
        open_hours=open_hours,
        bookings=bookings,
        excludes=[],
    )
    assert len(grid) == 1
    court = grid[0]
    assert court["location_id"] == "loc-1"
    assert court["sport"] == "tennis"
    slots = court["slots"]
    assert [s["start"] for s in slots] == ["09:00", "09:30", "10:00", "10:30"]
    available = {s["start"]: s["available"] for s in slots}
    assert available == {
        "09:00": True,
        "09:30": True,
        "10:00": False,  # booked
        "10:30": True,
    }


def test_build_availability_skips_disabled_courts():
    locations = [
        {"id": "open", "name": "A", "type": 0, "isEnabled": True},
        {"id": "closed", "name": "B", "type": 0, "isEnabled": False},
    ]
    open_hours = {"monday": {"from": "09:00:00", "to": "10:00:00"}}
    grid = build_availability(
        iso_date="2026-05-11",
        locations=locations,
        open_hours=open_hours,
        bookings=[],
        excludes=[],
    )
    assert [c["location_id"] for c in grid] == ["open"]


def test_build_availability_returns_empty_on_closed_day():
    locations = [{"id": "loc-1", "name": "A", "type": 0, "isEnabled": True}]
    # Sunday closed
    open_hours = {
        "monday": {"from": "09:00:00", "to": "23:00:00"},
        "sunday": {"from": None, "to": None},
    }
    # 2026-05-10 is a Sunday
    grid = build_availability(
        iso_date="2026-05-10",
        locations=locations,
        open_hours=open_hours,
        bookings=[],
        excludes=[],
    )
    assert grid == []


def test_build_availability_excludes_block_slots():
    locations = [
        {"id": "loc-1", "name": "A", "type": 0, "isEnabled": True},
        {"id": "loc-2", "name": "B", "type": 0, "isEnabled": True},
    ]
    open_hours = {"monday": {"from": "09:00:00", "to": "10:30:00"}}
    # exclude scoped to one location
    excludes = [
        {
            "locationId": "loc-1",
            "startHour": "09:30:00",
            "endHour": "10:00:00",
        }
    ]
    grid = build_availability(
        iso_date="2026-05-11",
        locations=locations,
        open_hours=open_hours,
        bookings=[],
        excludes=excludes,
    )
    by_loc = {c["location_id"]: c for c in grid}
    a_slots = {s["start"]: s["available"] for s in by_loc["loc-1"]["slots"]}
    b_slots = {s["start"]: s["available"] for s in by_loc["loc-2"]["slots"]}
    assert a_slots == {"09:00": True, "09:30": False, "10:00": True}
    # loc-2 unaffected
    assert b_slots == {"09:00": True, "09:30": True, "10:00": True}


def test_clubwide_exclude_blocks_all_locations():
    locations = [
        {"id": "loc-1", "name": "A", "type": 0, "isEnabled": True},
        {"id": "loc-2", "name": "B", "type": 0, "isEnabled": True},
    ]
    open_hours = {"monday": {"from": "09:00:00", "to": "10:00:00"}}
    excludes = [
        {"startHour": "09:00:00", "endHour": "09:30:00"}  # club-wide, no location scope
    ]
    grid = build_availability(
        iso_date="2026-05-11",
        locations=locations,
        open_hours=open_hours,
        bookings=[],
        excludes=excludes,
    )
    for court in grid:
        slots = {s["start"]: s["available"] for s in court["slots"]}
        assert slots == {"09:00": False, "09:30": True}
