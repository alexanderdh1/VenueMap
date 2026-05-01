from datetime import datetime, time

from pydantic import BaseModel


class Event(BaseModel):
    external_id: str
    title: str
    venue: str
    city: str
    event_url: str
    source: str
    start_datetime: datetime
    end_datetime: datetime | None = None
    doors_open: time | None = None
    genres: list[str] = []
    ticket_url: str | None = None
    ticket_status: str | None = None
    price: str | None = None
    image_url: str | None = None
