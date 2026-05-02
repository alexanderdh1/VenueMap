from abc import ABC, abstractmethod

from venuemap.models.event import Event

_REQUIRED = ("venue_id", "venue_name", "city_slug", "city_name", "latitude", "longitude")


class Scraper(ABC):
    venue_id: str
    venue_name: str
    city_slug: str
    city_name: str
    latitude: float
    longitude: float

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Raises at class definition time if a required attribute is missing,
        # before any instantiation or sync run.
        for attr in _REQUIRED:
            if not hasattr(cls, attr):
                raise TypeError(f"{cls.__name__} must define class attribute '{attr}'")

    @abstractmethod
    def fetch_events(self) -> list[Event]: ...
