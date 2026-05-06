from abc import ABC, abstractmethod

from venuemap.models.event import Event

_REQUIRED = ("venue_id", "venue_name", "city_slug", "city_name")


class Scraper(ABC):
    venue_id: str
    venue_name: str
    city_slug: str
    city_name: str
    address: str        # define address OR latitude+longitude
    latitude: float
    longitude: float

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Raises at class definition time if required attributes are missing,
        # before any instantiation or sync run.
        for attr in _REQUIRED:
            if not hasattr(cls, attr):
                raise TypeError(f"{cls.__name__} must define class attribute '{attr}'")
        has_coords = hasattr(cls, "latitude") and hasattr(cls, "longitude")
        has_address = hasattr(cls, "address")
        if not has_coords and not has_address:
            raise TypeError(
                f"{cls.__name__} must define either (latitude, longitude) or address"
            )

    @abstractmethod
    def fetch_events(self) -> list[Event]: ...
