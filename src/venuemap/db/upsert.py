import sys
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from venuemap.db.models import City, Event, Genre, ScrapeRun, Venue, event_genres
from venuemap.geocoding import geocode
from venuemap.models.event import Event as EventSchema


def get_or_create_venue(
    session: Session,
    venue_slug: str,
    venue_name: str,
    city_slug: str,
    city_name: str,
    latitude: float | None = None,
    longitude: float | None = None,
    address: str | None = None,
) -> Venue:
    venue = session.query(Venue).filter_by(slug=venue_slug).first()
    if venue:
        if latitude is not None:
            venue.latitude = latitude
            venue.longitude = longitude
        return venue

    # New venue without explicit coordinates — geocode from address
    if latitude is None and address:
        result = geocode(address)
        if result:
            latitude, longitude = result
            print(f"  Geocoded '{address}' → ({latitude:.6f}, {longitude:.6f})")
        else:
            print(f"  WARNING: could not geocode '{address}'", file=sys.stderr)

    city = session.query(City).filter_by(slug=city_slug).first()
    if not city:
        city = City(name=city_name, slug=city_slug)
        session.add(city)
        session.flush()

    venue = Venue(name=venue_name, slug=venue_slug, city_id=city.id, latitude=latitude, longitude=longitude)
    session.add(venue)
    session.flush()
    return venue


def get_or_create_genres(session: Session, names: list[str]) -> list[Genre]:
    genres = []
    for name in names:
        genre = session.query(Genre).filter_by(name=name).first()
        if not genre:
            genre = Genre(name=name)
            session.add(genre)
            session.flush()
        genres.append(genre)
    return genres


def upsert_events(session: Session, events: list[EventSchema], venue: Venue) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Drop past events before touching the DB
    upcoming = [e for e in events if e.start_datetime >= now]

    # Fetch all external_ids already stored for this venue in one query
    existing_rows = (
        session.query(Event.external_id, Event.id)
        .filter_by(venue_id=venue.id)
        .all()
    )
    existing = {row.external_id: row.id for row in existing_rows}

    new_count = 0
    updated_count = 0

    for schema in upcoming:
        genres = get_or_create_genres(session, schema.genres)

        if schema.external_id not in existing:
            # Insert
            db_event = Event(
                external_id=schema.external_id,
                venue_id=venue.id,
                title=schema.title,
                event_url=schema.event_url,
                source=schema.source,
                start_datetime=schema.start_datetime,
                end_datetime=schema.end_datetime,
                doors_open=schema.doors_open,
                ticket_url=schema.ticket_url,
                ticket_status=schema.ticket_status,
                price=schema.price,
                image_url=schema.image_url,
                first_seen_at=now,
                last_seen_at=now,
            )
            db_event.genres = genres
            session.add(db_event)
            new_count += 1
        else:
            # Update mutable fields; preserve first_seen_at
            db_event = session.get(Event, existing[schema.external_id])
            db_event.title = schema.title
            db_event.event_url = schema.event_url
            db_event.start_datetime = schema.start_datetime
            db_event.end_datetime = schema.end_datetime
            db_event.doors_open = schema.doors_open
            db_event.ticket_url = schema.ticket_url
            db_event.ticket_status = schema.ticket_status
            db_event.price = schema.price
            db_event.image_url = schema.image_url
            db_event.last_seen_at = now
            db_event.genres = genres
            updated_count += 1

    session.commit()
    return {"new": new_count, "updated": updated_count, "total_upcoming": len(upcoming)}


def record_scrape_run(
    session: Session,
    venue: Venue,
    started_at: datetime,
    events_found: int,
    new_count: int,
    updated_count: int,
    error: str | None = None,
) -> None:
    run = ScrapeRun(
        venue_id=venue.id,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
        events_found=events_found,
        events_new=new_count,
        events_updated=updated_count,
        error=error,
    )
    session.add(run)
    session.commit()
