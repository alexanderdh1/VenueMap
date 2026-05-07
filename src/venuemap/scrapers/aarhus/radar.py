import json
import re
import time
from datetime import datetime
from datetime import time as Time
from datetime import timezone

import httpx
from bs4 import BeautifulSoup

from venuemap.models.event import Event
from venuemap.scrapers.base import Scraper

_BASE = "https://radarlive.dk"
_CALENDAR_URL = f"{_BASE}/kalender/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VenueMap/1.0)"}

_DANISH_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "maj": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
}
_KALENDER_RE = re.compile(r"^/kalender/(\d{4})/\w+/[^/]+/?$")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


class RadarScraper(Scraper):
    venue_id = "radar-aarhus"
    venue_name = "Radar"
    city_slug = "aarhus"
    city_name = "Aarhus"
    address = "Karen Wegeners Gade 6, Aarhus, Denmark"

    def fetch_events(self) -> list[Event]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = []

        with httpx.Client(timeout=15.0, headers=_HEADERS, follow_redirects=True) as client:
            listings = self._fetch_listings(client, now)
            for listing in listings:
                try:
                    event = self._fetch_event(client, listing)
                    if event and event.start_datetime >= now:
                        events.append(event)
                except Exception as e:
                    print(f"Warning: skipped {listing['slug']} — {e}")
                time.sleep(0.3)

        return sorted(events, key=lambda e: e.start_datetime)

    # --- Stage 1: calendar listing ---

    def _fetch_listings(self, client, now: datetime) -> list[dict]:
        resp = client.get(_CALENDAR_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for a in soup.find_all("a", class_="article", href=True):
            path = a["href"].split("?")[0]
            m = _KALENDER_RE.match(path)
            if not m:
                continue
            year = int(m.group(1))
            slug = path.strip("/").split("/")[-1]

            day_el = a.find("span", class_="day")
            month_el = a.find("span", class_="month")
            if not day_el or not month_el:
                continue
            month = _DANISH_MONTHS.get(month_el.get_text(strip=True).lower())
            if month is None:
                continue
            try:
                start_date = datetime(year, month, int(day_el.get_text(strip=True)))
            except ValueError:
                continue
            if start_date.date() < now.date():
                continue

            h2 = a.find("h2")
            if h2 is None:
                continue

            img = a.find("img")

            results.append({
                "slug": slug,
                "title": h2.get_text(strip=True),
                "start_date": start_date,
                "event_url": f"{_BASE}{path}",
                "image_url": (_BASE + img["src"] if img and img["src"].startswith("/") else img["src"] if img else None),
            })

        return results

    # --- Stage 2: event detail page ---

    def _fetch_event(self, client, listing: dict) -> Event | None:
        resp = client.get(listing["event_url"])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        sidebar = soup.find("aside", class_="event-sidebar")
        if sidebar is None:
            return None

        hours_el = sidebar.find("div", class_="val-hours")
        doors, concert_time = _parse_hours(hours_el.get_text(strip=True) if hours_el else "")

        start_dt = listing["start_date"]
        if concert_time:
            start_dt = start_dt.replace(hour=concert_time.hour, minute=concert_time.minute)

        price_el = sidebar.find("div", class_="val-price")
        genre_el = sidebar.find("div", class_="val-genre")
        ticket_el = sidebar.find("a", class_="ticket")

        return Event(
            external_id=listing["slug"],
            title=listing["title"],
            venue=self.venue_name,
            city=self.city_slug,
            event_url=listing["event_url"],
            ticket_url=ticket_el["href"] if ticket_el else None,
            source="html",
            start_datetime=start_dt,
            doors_open=doors,
            genres=[genre_el.get_text(strip=True)] if genre_el else [],
            price=price_el.get_text(strip=True) if price_el else None,
            image_url=listing["image_url"],
        )


# --- Helpers ---

def _parse_hours(text: str) -> tuple[Time | None, Time | None]:
    # Format: "19:00/20:00" → (doors, concert)
    times = _TIME_RE.findall(text)
    def to_time(t):
        try:
            return Time(int(t[0]), int(t[1]))
        except ValueError:
            return None
    doors = to_time(times[0]) if len(times) > 0 else None
    concert = to_time(times[1]) if len(times) > 1 else None
    return doors, concert


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching events...", file=sys.stderr)
    scraper = RadarScraper()
    events = scraper.fetch_events()
    print(f"Done. {len(events)} upcoming events.", file=sys.stderr)
    print(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False))
