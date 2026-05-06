import httpx

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def geocode(address: str) -> tuple[float, float] | None:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            _NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "VenueMap/1.0 (alexander@hougaard.org)"},
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])
