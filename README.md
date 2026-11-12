# Meeting Room Booking API

A small REST API for booking meeting rooms in an office. Employees can list rooms, check which rooms are free for a time slot, book a room, and cancel a booking. Two confirmed bookings can never overlap in the same room.

Built with **Python** and **FastAPI**. Storage is in memory, so there is no database or auth to set up.

---

## Features

- List rooms, with seeded sample data
- Check availability for a time range, with an optional minimum capacity filter
- Book a room, with validation and conflict detection
- Cancel a booking (soft delete), which frees the slot immediately
- List bookings, with optional filters by room and by person, sorted by start time
- Interactive API docs at `/docs` (Swagger UI)

---

## Project structure

```
meeting-room-api/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app and endpoints
│   ├── models.py           # Pydantic request model
│   ├── store.py            # In-memory data and seeded rooms
│   └── booking_logic.py    # Pure functions: overlaps, find_conflicts
├── tests/
│   ├── test_booking_logic.py   # Unit tests for the overlap rules (9)
│   └── test_api.py             # Endpoint tests (13)
├── pytest.ini
├── requirements.txt
└── README.md
```

**Why this split:** the overlap logic lives in `booking_logic.py` as pure functions with no FastAPI dependency. That makes the core rule easy to unit test, and it lets booking and availability share one implementation, so the two endpoints can never disagree.

---

## Setup

**Requirements:** Python 3.11+

```bash
cd meeting-room-api
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run the server

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs

`--reload` restarts the server on every file save. Because storage is in memory, **each restart clears all bookings**. The three seeded rooms come back.

## Run the tests

```bash
pytest -v
```

Expected: **22 passed** (9 logic tests and 13 API tests).

You may see a `StarletteDeprecationWarning` about `httpx` in the test client. It comes from the library, not this code, and does not affect results.

---

## Seeded rooms

| id | name | capacity |
|---|---|---|
| 1 | Everest | 10 |
| 2 | Kilimanjaro | 6 |
| 3 | Fuji | 4 |

---

## API reference

All datetimes are ISO 8601 without a timezone, for example `2026-12-01T10:00:00`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/rooms` | List all rooms |
| GET | `/rooms/available` | Rooms free for a time range |
| POST | `/bookings` | Create a booking |
| GET | `/bookings` | List bookings, with optional filters |
| DELETE | `/bookings/{booking_id}` | Cancel a booking |

### GET /rooms

Returns all rooms.

```bash
curl http://127.0.0.1:8000/rooms
```

### GET /rooms/available

| Query param | Type | Required | Description |
|---|---|---|---|
| `start` | datetime | yes | Start of the requested slot |
| `end` | datetime | yes | End of the requested slot |
| `min_capacity` | int | no | Only rooms with at least this capacity |

```bash
curl "http://127.0.0.1:8000/rooms/available?start=2026-12-01T10:00:00&end=2026-12-01T11:00:00&min_capacity=5"
```

Returns `200` with a list of free rooms (possibly empty), or `422` if `end` is not after `start`.

### POST /bookings

Request body:

```json
{
  "room_id": 1,
  "booked_by": "manish",
  "start": "2026-12-01T10:00:00",
  "end": "2026-12-01T11:00:00"
}
```

```bash
curl -X POST http://127.0.0.1:8000/bookings \
  -H "Content-Type: application/json" \
  -d '{"room_id":1,"booked_by":"manish","start":"2026-12-01T10:00:00","end":"2026-12-01T11:00:00"}'
```

Success (`201`):

```json
{
  "id": "7eda0113-e62f-43c2-bd19-d6e1bffe3514",
  "room_id": 1,
  "booked_by": "manish",
  "start": "2026-12-01T10:00:00",
  "end": "2026-12-01T11:00:00",
  "status": "confirmed"
}
```

### GET /bookings

| Query param | Type | Required | Description |
|---|---|---|---|
| `room_id` | int | no | Only bookings for this room |
| `booked_by` | string | no | Only bookings made by this person |

Results are sorted by `start`, earliest first. **Cancelled bookings are included**, with `"status": "cancelled"`.

### DELETE /bookings/{booking_id}

Cancels a booking by setting its status to `cancelled`. It is a soft delete, so the record stays in the system.

```bash
curl -X DELETE http://127.0.0.1:8000/bookings/<booking_id>
```

---

## Business rules and status codes

| Situation | Status | Detail |
|---|---|---|
| Booking created | 201 | Returns the booking with a uuid |
| `end` is not after `start` | 422 | `end must be after start` |
| Duration over 4 hours | 422 | `booking cannot exceed 4 hours` |
| Missing or wrong-typed field, or empty `booked_by` | 422 | FastAPI validation error |
| Room does not exist | 404 | `room not found` |
| Overlaps a confirmed booking in the same room | 409 | `conflicts with booking <id>` |
| Cancel succeeds | 200 | Returns the booking with `status: cancelled` |
| Cancel an unknown id | 404 | `booking not found` |
| Cancel an already cancelled booking | 409 | `booking already cancelled` |

**Validation order in `POST /bookings`:** cheap checks first (time range, duration, room exists), then the conflict check.

---

## Key design decisions

**1. Overlap rule.** Two ranges overlap if each one starts before the other ends:

```python
start_a < end_b and start_b < end_a
```

The comparison is strict, so **the end time is exclusive**. A booking from 10:00 to 11:00 and another from 11:00 to 12:00 do not conflict. Back-to-back meetings are normal in an office, and using `<=` would wrongly reject them.

**2. One shared conflict function.** `find_conflicts` is used by both `POST /bookings` and `GET /rooms/available`. If they had separate logic, a client could be shown a room as free and then have the booking rejected.

**3. Soft delete.** Cancelling sets `status = "cancelled"` instead of removing the record. `find_conflicts` only considers `confirmed` bookings, so a cancelled booking frees its slot with no extra code, and booking history is preserved.

**4. Pure logic separated from I/O.** The overlap functions take plain datetimes and dicts. They are tested without starting a server.

**5. Scoped conflict check.** Conflicts are checked only against bookings in the requested room, not against every booking in the system.

---

## Assumptions

- Datetimes are naive (no timezone). All times are treated as one local office time.
- Maximum booking length is 4 hours.
- Rooms are predefined in code. There is no endpoint to create rooms.
- No authentication. `booked_by` is a plain string and is not verified.
- Storage is in memory and is lost on restart.
- Cancelled bookings remain visible in `GET /bookings`.
- No recurring bookings, no booking edits, and no business-hours restriction.

---

## Known limitations

- **Race condition.** Conflict check and insert are two separate steps. Two simultaneous requests for the same room and slot could both pass the check. This is not safe across multiple workers or servers.
- **No persistence.** A restart wipes all bookings.
- **Timezones.** Sending a timezone-aware datetime alongside naive ones raises a `TypeError` on comparison, which returns a 500.
- **Linear scan.** Each conflict check scans all bookings for the room. That is fine for a demo but will not scale to a large dataset.
- **No pagination** on `GET /bookings`.
- `min_capacity` accepts zero and negative values without complaint.

---

## What I would do next

1. **Fix the race condition.** Move to Postgres and add an exclusion constraint on `(room_id, tstzrange(start, end))`, so the database itself rejects overlapping bookings. For a single process, a per-room lock is a quick stopgap.
2. **Timezones.** Store everything in UTC and convert at the edges.
3. **Persistence.** Replace the in-memory store with a database, with an index on `(room_id, start)`.
4. **Filtering and pagination.** Add `?status=confirmed` and paginate `GET /bookings`.
5. **Auth.** Identify the user from a token instead of a free-text `booked_by`, and only let owners cancel their own bookings.
6. **Recurring bookings.** Store a recurrence rule, expand it into concrete bookings, and run each through the same conflict check.
7. **Extract a validation helper** for the `end > start` check that currently appears in two endpoints.

---

## Testing

| File | Tests | Covers |
|---|---|---|
| `tests/test_booking_logic.py` | 9 | `overlaps` (back-to-back, partial, contained, identical, disjoint) and `find_conflicts` (overlap, back-to-back, cancelled, empty list) |
| `tests/test_api.py` | 13 | Conflict 409, different room, back-to-back, cancel and rebook, 422 and 404 validation, availability, and the full cancel flow (200, 404, 409, slot freed, only the target changes, history kept) |

An autouse fixture resets the in-memory store before every test, so tests are independent of each other.

To check the tests catch real bugs, temporarily change `<` to `<=` in `overlaps` and confirm the back-to-back tests fail. Then revert the change.