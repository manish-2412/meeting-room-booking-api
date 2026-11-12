import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException

from app import store
from app.booking_logic import find_conflicts
from app.models import BookingCreate

app = FastAPI(title="Meeting Room Booking")

MAX_DURATION = timedelta(hours=4)


def bookings_for_room(room_id: int) -> list[dict]:
    return [b for b in store.bookings.values() if b["room_id"] == room_id]


@app.get("/rooms")
def list_rooms():
    return list(store.rooms.values())


@app.get("/rooms/available")
def available_rooms(start: datetime, end: datetime, min_capacity: Optional[int] = None):
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be after start")

    available = []
    for room in store.rooms.values():
        if min_capacity is not None and room["capacity"] < min_capacity:
            continue
        # Same conflict function as booking, so the two can never disagree
        if not find_conflicts(start, end, bookings_for_room(room["id"])):
            available.append(room)
    return available


@app.post("/bookings", status_code=201)
def create_booking(payload: BookingCreate):
    if payload.end <= payload.start:
        raise HTTPException(status_code=422, detail="end must be after start")
    if payload.end - payload.start > MAX_DURATION:
        raise HTTPException(status_code=422, detail="booking cannot exceed 4 hours")
    if payload.room_id not in store.rooms:
        raise HTTPException(status_code=404, detail="room not found")

    room_bookings = bookings_for_room(payload.room_id)
    conflicts = find_conflicts(payload.start, payload.end, room_bookings)
    if conflicts:
        raise HTTPException(status_code=409, detail=f"conflicts with booking {conflicts[0]['id']}")

    booking = {"id": str(uuid.uuid4()), **payload.model_dump(), "status": "confirmed"}
    store.bookings[booking["id"]] = booking
    return booking

@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    booking = store.bookings.get(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="booking already cancelled")
    booking["status"] = "cancelled"  # soft delete; find_conflicts ignores it
    return booking


@app.get("/bookings")
def list_bookings(room_id: Optional[int] = None, booked_by: Optional[str] = None):
    results = list(store.bookings.values())
    if room_id is not None:
        results = [b for b in results if b["room_id"] == room_id]
    if booked_by is not None:
        results = [b for b in results if b["booked_by"] == booked_by]
    return sorted(results, key=lambda b: b["start"])