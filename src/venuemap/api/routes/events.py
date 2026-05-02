from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from venuemap.api.deps import get_db
from venuemap.api.schemas import EventResponse, EventsResponse, VenueShort
from venuemap.db.models import City, Event, Genre, Venue

router = APIRouter()

_DEFAULT_WINDOW_DAYS = 60


@router.get("/events", response_model=EventsResponse)
def get_events(
    venue: str | None = Query(None, description="Venue slug, e.g. voxhall-aarhus"),
    city: str | None = Query(None, description="City slug, e.g. aarhus"),
    genre: str | None = Query(None, description="Genre name, e.g. Rock"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    windowed = date_to is None
    effective_date_to = date_to if date_to is not None else now + timedelta(days=_DEFAULT_WINDOW_DAYS)

    q = (
        db.query(Event)
        .options(
            joinedload(Event.venue).joinedload(Venue.city),
            joinedload(Event.genres),
        )
        .filter(Event.start_datetime >= now)
        .filter(Event.start_datetime <= effective_date_to)
    )

    if venue or city:
        q = q.join(Event.venue)
        if venue:
            q = q.filter(Venue.slug == venue)
        if city:
            q = q.join(Venue.city).filter(City.slug == city)

    if genre:
        q = q.filter(Event.genres.any(Genre.name == genre))

    if date_from:
        q = q.filter(Event.start_datetime >= date_from)

    q = q.order_by(Event.start_datetime)
    rows = q.all()

    # Check if events exist beyond the default window (only relevant when window is active)
    has_events_beyond_window = False
    if windowed:
        has_events_beyond_window = (
            db.query(Event.id)
            .filter(Event.start_datetime > effective_date_to)
            .first()
            is not None
        )

    return EventsResponse(
        events=[_to_response(e) for e in rows],
        has_events_beyond_window=has_events_beyond_window,
    )


def _to_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        title=event.title,
        venue=VenueShort(slug=event.venue.slug, name=event.venue.name),
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        doors_open=event.doors_open,
        genres=[g.name for g in event.genres],
        ticket_url=event.ticket_url,
        ticket_status=event.ticket_status,
        price=event.price,
        image_url=event.image_url,
        event_url=event.event_url,
    )
