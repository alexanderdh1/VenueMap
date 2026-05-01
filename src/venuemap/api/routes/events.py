from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from venuemap.api.deps import get_db
from venuemap.api.schemas import EventResponse, EventsPage, VenueShort
from venuemap.db.models import City, Event, Genre, Venue

router = APIRouter()


@router.get("/events", response_model=EventsPage)
def get_events(
    venue: str | None = Query(None, description="Venue slug, e.g. voxhall-aarhus"),
    city: str | None = Query(None, description="City slug, e.g. aarhus"),
    genre: str | None = Query(None, description="Genre name, e.g. Rock"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    q = (
        db.query(Event)
        .options(
            joinedload(Event.venue).joinedload(Venue.city),
            joinedload(Event.genres),
        )
        .filter(Event.start_datetime >= now)
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
    if date_to:
        q = q.filter(Event.start_datetime <= date_to)

    q = q.order_by(Event.start_datetime)

    total = q.count()
    rows = q.offset((page - 1) * per_page).limit(per_page).all()

    return EventsPage(
        events=[_to_response(e) for e in rows],
        total=total,
        page=page,
        per_page=per_page,
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
