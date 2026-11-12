import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    store.reset()
    yield


def book(room_id=1, start="2026-12-01T10:00:00", end="2026-12-01T11:00:00"):
    return client.post("/bookings", json={
        "room_id": room_id, "booked_by": "manish", "start": start, "end": end,
    })


# ---------- Booking and availability ----------

def test_overlapping_slot_returns_409():
    assert book().status_code == 201
    assert book(start="2026-12-01T10:30:00", end="2026-12-01T11:30:00").status_code == 409


def test_same_slot_different_room_returns_201():
    assert book(room_id=1).status_code == 201
    assert book(room_id=2).status_code == 201


def test_back_to_back_returns_201():
    assert book().status_code == 201
    assert book(start="2026-12-01T11:00:00", end="2026-12-01T12:00:00").status_code == 201


def test_cancel_then_rebook_returns_201():
    booking_id = book().json()["id"]
    assert client.delete(f"/bookings/{booking_id}").status_code == 200
    assert book().status_code == 201


def test_end_before_start_returns_422():
    assert book(start="2026-12-01T11:00:00", end="2026-12-01T10:00:00").status_code == 422


def test_unknown_room_returns_404():
    assert book(room_id=99).status_code == 404


def test_available_hides_booked_room():
    book()
    response = client.get("/rooms/available", params={
        "start": "2026-12-01T10:00:00", "end": "2026-12-01T11:00:00",
    })
    names = [room["name"] for room in response.json()]
    assert "Everest" not in names
    assert len(names) == 2


# ---------- Delete ----------

def test_cancel_returns_200_and_cancelled_status():
    booking_id = book().json()["id"]
    response = client.delete(f"/bookings/{booking_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_unknown_id_returns_404():
    assert client.delete("/bookings/fake-id").status_code == 404


def test_cancel_twice_returns_409():
    booking_id = book().json()["id"]
    assert client.delete(f"/bookings/{booking_id}").status_code == 200
    assert client.delete(f"/bookings/{booking_id}").status_code == 409


def test_cancel_frees_slot_in_availability():
    booking_id = book().json()["id"]
    params = {"start": "2026-12-01T10:00:00", "end": "2026-12-01T11:00:00"}

    before = [r["name"] for r in client.get("/rooms/available", params=params).json()]
    assert "Everest" not in before

    client.delete(f"/bookings/{booking_id}")

    after = [r["name"] for r in client.get("/rooms/available", params=params).json()]
    assert "Everest" in after


def test_cancel_only_affects_target_booking():
    first_id = book().json()["id"]
    book(start="2026-12-01T11:00:00", end="2026-12-01T12:00:00")

    client.delete(f"/bookings/{first_id}")

    statuses = {b["id"]: b["status"] for b in client.get("/bookings").json()}
    assert statuses[first_id] == "cancelled"
    assert list(statuses.values()).count("confirmed") == 1


def test_cancelled_booking_still_appears_in_list():
    booking_id = book().json()["id"]
    client.delete(f"/bookings/{booking_id}")
    bookings = client.get("/bookings").json()
    assert len(bookings) == 1
    assert bookings[0]["status"] == "cancelled"