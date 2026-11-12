from datetime import datetime

def overlaps(start_a: datetime, end_a: datetime,
             start_b: datetime, end_b: datetime) -> bool:
    # Strict < so back-to-back bookings (11:00 end, 11:00 start) are allowed
    return start_a < end_b and start_b < end_a


def find_conflicts(new_start: datetime, new_end: datetime, bookings: list[dict]) -> list[dict]:
    return [
        booking for booking in bookings
        if booking["status"] == "confirmed"
        and overlaps(new_start, new_end, booking["start"], booking["end"])
    ]