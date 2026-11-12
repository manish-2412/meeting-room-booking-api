from datetime import datetime
from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    room_id: int
    booked_by: str = Field(min_length=1)
    start: datetime
    end: datetime