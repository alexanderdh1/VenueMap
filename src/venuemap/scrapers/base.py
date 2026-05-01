from abc import ABC, abstractmethod

from venuemap.models.event import Event


class Scraper(ABC):
    venue_id: str
    venue_name: str
    city_slug: str
    city_name: str
    latitude: float
    longitude: float

    @abstractmethod
    def fetch_events(self) -> list[Event]: ...
