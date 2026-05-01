from datetime import datetime, time

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# Junction table — no model class needed, just a table
event_genres = Table(
    "event_genres",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)  # e.g. "aarhus"

    venues = relationship("Venue", back_populates="city")


class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)  # e.g. "voxhall-aarhus"
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)

    city = relationship("City", back_populates="venues")
    events = relationship("Event", back_populates="venue")
    scrape_runs = relationship("ScrapeRun", back_populates="venue")


class Genre(Base):
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    events = relationship("Event", secondary=event_genres, back_populates="genres")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    external_id = Column(String, nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    title = Column(String, nullable=False)
    event_url = Column(String, nullable=False)
    source = Column(String, nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=True)
    doors_open = Column(Time, nullable=True)
    ticket_url = Column(String, nullable=True)
    ticket_status = Column(String, nullable=True)
    price = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    first_seen_at = Column(DateTime, nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime, nullable=False, server_default=func.now())

    venue = relationship("Venue", back_populates="events")
    genres = relationship("Genre", secondary=event_genres, back_populates="events")

    __table_args__ = (
        UniqueConstraint("external_id", "venue_id", name="uq_event_external_venue"),
    )


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    events_found = Column(Integer, nullable=True)
    events_new = Column(Integer, nullable=True)
    events_updated = Column(Integer, nullable=True)
    error = Column(String, nullable=True)

    venue = relationship("Venue", back_populates="scrape_runs")
