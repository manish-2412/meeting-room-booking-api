rooms = {
    1: {"id": 1, "name": "Everest", "capacity": 10},
    2: {"id": 2, "name": "Kilimanjaro", "capacity": 6},
    3: {"id": 3, "name": "Fuji", "capacity": 4},
}

bookings: dict[str, dict] = {}  # booking_id -> booking


def reset():
    bookings.clear()  # lets tests start from a clean slate