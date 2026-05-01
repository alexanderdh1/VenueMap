from datetime import datetime, time

from pydantic import BaseModel


class VenueShort(BaseModel):
    slug: str
    name: str


class VenueResponse(BaseModel):
    slug: str
    name: str
    city: str
    latitude: float | None
    longitude: float | None


class EventResponse(BaseModel):
    id: int
    title: str
    venue: VenueShort
    start_datetime: datetime
    end_datetime: datetime | None = None
    doors_open: time | None = None
    genres: list[str]
    ticket_url: str | None = None
    ticket_status: str | None = None
    price: str | None = None
    image_url: str | None = None
    event_url: str


class EventsPage(BaseModel):
    events: list[EventResponse]
    total: int
    page: int
    per_page: int
