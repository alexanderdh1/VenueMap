import json
import re
from datetime import datetime, timezone
from hashlib import md5

import httpx
from bs4 import BeautifulSoup

from venuemap.models.event import Event
from venuemap.scrapers.base import Scraper

_EVENTS_URL = "https://www.erlings.dk/begivenheder"

_DANISH_MONTHS = {
    "januar": 1, "jan": 1,
    "februar": 2, "feb": 2,
    "marts": 3, "mar": 3,
    "april": 4, "apr": 4,
    "maj": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Matches the start of a date string: "09. maj 2026, 15.00"
_START_DT_RE = re.compile(
    r"(\d{1,2})\.\s*(\w+\.?)\s+(\d{4}),\s*(\d{1,2})\.(\d{2})"
)
_PRICE_RE = re.compile(r"(\d[\d\s]*\s*DKK|Gratis\s+entré)", re.IGNORECASE)


class ErlingsScraper(Scraper):
    venue_id = "erlings-aarhus"
    venue_name = "Erlings Jazz- & Ølbar"
    city_slug = "aarhus"
    city_name = "Aarhus"
    latitude = 56.1606320
    longitude = 10.2133660

    def fetch_events(self) -> list[Event]:
        html = self._fetch_page()
        soup = BeautifulSoup(html, "lxml")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = []

        for item in soup.find_all("li", {"data-hook": "event-list-item"}):
            try:
                event = self._parse_item(item)
                if event is not None and event.start_datetime >= now:
                    events.append(event)
            except Exception as e:
                title = item.find("span", {"data-hook": "ev-list-item-title"})
                label = title.get_text(strip=True) if title else "?"
                print(f"Warning: skipped '{label}' — {e}")

        return sorted(events, key=lambda e: e.start_datetime)

    def _fetch_page(self) -> str:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                _EVENTS_URL,
                headers={"User-Agent": "Mozilla/5.0 (compatible; VenueMap/1.0)"},
            )
            resp.raise_for_status()
            return resp.text

    def _parse_item(self, item) -> Event | None:
        title_tag = item.find("span", {"data-hook": "ev-list-item-title"})
        if title_tag is None:
            return None
        title = title_tag.get_text(strip=True)

        date_tag = item.find(attrs={"data-hook": "date"})
        if date_tag is None:
            return None
        start_dt = self._parse_start_dt(date_tag.get_text(strip=True))
        if start_dt is None:
            return None

        desc_tag = item.find(attrs={"data-hook": "ev-list-item-description"})
        desc_text = desc_tag.get_text(strip=True) if desc_tag else ""

        rsvp = item.find("a", {"data-hook": "ev-rsvp-button"})
        ticket_url = rsvp["href"] if rsvp else None
        event_url = ticket_url or _EVENTS_URL

        # Stable ID: hash of venue + title + start time (no DB-assigned IDs available)
        external_id = md5(
            f"{self.venue_id}:{title}:{start_dt.isoformat()}".encode()
        ).hexdigest()[:16]

        return Event(
            external_id=external_id,
            title=title,
            venue=self.venue_name,
            city=self.city_slug,
            event_url=event_url,
            ticket_url=ticket_url,
            source="html",
            start_datetime=start_dt,
            price=self._parse_price(title + " " + desc_text),
        )

    def _parse_start_dt(self, date_text: str) -> datetime | None:
        # Format: "09. maj 2026, 15.00 – 17.00"
        m = _START_DT_RE.search(date_text)
        if not m:
            return None
        day, month_raw, year, hour, minute = m.groups()
        month = _DANISH_MONTHS.get(month_raw.rstrip(".").lower())
        if month is None:
            return None
        try:
            return datetime(int(year), month, int(day), int(hour), int(minute))
        except ValueError:
            return None

    def _parse_price(self, text: str) -> str | None:
        m = _PRICE_RE.search(text)
        return m.group(0).strip() if m else None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching events...", file=sys.stderr)
    scraper = ErlingsScraper()
    events = scraper.fetch_events()
    print(f"Done. {len(events)} upcoming events.", file=sys.stderr)
    print(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False))
