import html
import json
from datetime import datetime, timezone

import httpx

from venuemap import http
from venuemap.models.event import Event
from venuemap.scrapers.base import Scraper

_BASE = "https://www.turkislive.com"
_API_URL = f"{_BASE}/koncerter?format=json"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VenueMap/1.0)"}


class TurkisScraper(Scraper):
    venue_id = "turkis-aarhus"
    venue_name = "Turkis"
    city_slug = "aarhus"
    city_name = "Aarhus"
    address = "Vester Allé 15, Aarhus, Denmark"

    def fetch_events(self) -> list[Event]:
        with httpx.Client(timeout=15.0, headers=_HEADERS, follow_redirects=True) as client:
            resp = http.get(client, _API_URL)
            data = resp.json()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = []

        for item in data.get("upcoming", []):
            try:
                event = self._parse_item(item)
                if event and event.start_datetime >= now:
                    events.append(event)
            except Exception as e:
                print(f"Warning: skipped {item.get('urlId', '?')} — {e}")

        return sorted(events, key=lambda e: e.start_datetime)

    def _parse_item(self, item: dict) -> Event | None:
        start_ms = item.get("startDate")
        if not start_ms:
            return None
        start_dt = datetime.fromtimestamp(start_ms / 1000)

        end_ms = item.get("endDate")
        end_dt = datetime.fromtimestamp(end_ms / 1000) if end_ms else None

        title = html.unescape(item.get("title", "")).strip()
        if not title:
            return None

        slug = item["urlId"]
        return Event(
            external_id=item["id"],
            title=title,
            venue=self.venue_name,
            city=self.city_slug,
            event_url=f"{_BASE}{item['fullUrl']}",
            source="json",
            start_datetime=start_dt,
            end_datetime=end_dt,
            genres=[],
            image_url=item.get("assetUrl"),
        )


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching events...", file=sys.stderr)
    scraper = TurkisScraper()
    events = scraper.fetch_events()
    print(f"Done. {len(events)} upcoming events.", file=sys.stderr)
    print(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False))
