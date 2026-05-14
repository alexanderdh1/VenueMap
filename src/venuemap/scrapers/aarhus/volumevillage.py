import json
import re
import time
from datetime import datetime
from datetime import time as Time
from datetime import timezone

import httpx
from bs4 import BeautifulSoup

from venuemap import http
from venuemap.models.event import Event
from venuemap.scrapers.base import Scraper

_BASE = "https://www.volumevillage.dk"
_EVENTS_URL = f"{_BASE}/events"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VenueMap/1.0)"}
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


class VolumeVillageScraper(Scraper):
    venue_id = "volume-village-aarhus"
    venue_name = "Volume Village"
    city_slug = "aarhus"
    city_name = "Aarhus"
    address = "Thomas Koppels Gade 201, Aarhus, Denmark"

    def fetch_events(self) -> list[Event]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = []

        with httpx.Client(timeout=15.0, headers=_HEADERS) as client:
            listings = self._fetch_listings(client, now)
            for listing in listings:
                try:
                    event = self._enrich(client, listing)
                    if event and event.start_datetime >= now:
                        events.append(event)
                except Exception as e:
                    print(f"Warning: skipped {listing['slug']} — {e}")
                time.sleep(0.3)

        return sorted(events, key=lambda e: e.start_datetime)

    # --- Stage 1: listing page ---

    def _fetch_listings(self, client, now: datetime) -> list[dict]:
        resp = http.get(client, _EVENTS_URL)
        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for card in soup.find_all("div", class_="collection-event-og-nyheder-overview"):
            try:
                listing = self._parse_card(card)
                if listing is None:
                    continue
                if listing["start_date"].date() < now.date():
                    continue
                results.append(listing)
            except Exception as e:
                print(f"Warning: skipped card — {e}")

        return results

    def _parse_card(self, card) -> dict | None:
        title_link = card.find("a", class_="heading-2")
        if title_link is None:
            return None
        title = title_link.get_text(strip=True)
        href = title_link.get("href", "")
        if not href.startswith("/events/"):
            return None
        slug = href.removeprefix("/events/")

        date_divs = card.find_all("div", class_="event_cms_date")
        if not date_divs:
            return None
        start_date = _parse_date(date_divs[0].get_text(strip=True))
        if start_date is None:
            return None

        img = card.find("img", class_="image-for-events")
        ticket_link = card.find("a", class_="alle-events")

        return {
            "slug": slug,
            "title": title,
            "start_date": start_date,
            "event_url": f"{_BASE}{href}",
            "ticket_url": ticket_link["href"] if ticket_link else None,
            "image_url": img["src"] if img else None,
        }

    # --- Stage 2: detail page ---

    def _enrich(self, client, listing: dict) -> Event | None:
        resp = http.get(client, listing["event_url"])
        soup = BeautifulSoup(resp.text, "lxml")

        start_time = _parse_right_time(soup, tag="div")
        doors = _parse_right_time(soup, tag="h2")

        start_dt = listing["start_date"]
        if start_time:
            start_dt = start_dt.replace(hour=start_time.hour, minute=start_time.minute)

        return Event(
            external_id=listing["slug"],
            title=listing["title"],
            venue=self.venue_name,
            city=self.city_slug,
            event_url=listing["event_url"],
            ticket_url=listing["ticket_url"],
            source="html",
            start_datetime=start_dt,
            doors_open=doors,
            price=_parse_price(soup),
            image_url=listing["image_url"],
        )


# --- Helpers ---

def _parse_date(date_str: str) -> datetime | None:
    # Format: "14.5.2026" — single-digit month/day possible
    parts = date_str.strip().split(".")
    if len(parts) != 3:
        return None
    try:
        return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
    except ValueError:
        return None


def _parse_right_time(soup: BeautifulSoup, tag: str) -> Time | None:
    # Detail page: left column has labels, right column has times.
    # h2.right = doors open, div.right = show start.
    for el in soup.find_all(tag):
        classes = el.get("class", [])
        if "right" in classes and "date_time_ticket-price" in classes:
            m = _TIME_RE.search(el.get_text(strip=True))
            if m:
                try:
                    return Time(int(m.group(1)), int(m.group(2)))
                except ValueError:
                    pass
    return None


def _parse_price(soup: BeautifulSoup) -> str | None:
    block = soup.find("div", class_="div-block-29")
    if not block:
        return None
    parts = [d.get_text(strip=True) for d in block.find_all("div") if d.get_text(strip=True)]
    return " ".join(parts) if parts else None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching events...", file=sys.stderr)
    scraper = VolumeVillageScraper()
    events = scraper.fetch_events()
    print(f"Done. {len(events)} upcoming events.", file=sys.stderr)
    print(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False))
