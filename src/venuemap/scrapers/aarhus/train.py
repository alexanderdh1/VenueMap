import json
import time
from datetime import datetime
from datetime import time as Time
from datetime import timezone

import httpx
from bs4 import BeautifulSoup

from venuemap.models.event import Event
from venuemap.scrapers.base import Scraper

_BASE = "https://train.dk"
_CALENDAR_URL = f"{_BASE}/kalender"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VenueMap/1.0)"}


class TrainScraper(Scraper):
    venue_id = "train-aarhus"
    venue_name = "TRAIN"
    city_slug = "aarhus"
    city_name = "Aarhus"
    address = "Toldbodgade 6, Aarhus, Denmark"

    def fetch_events(self) -> list[Event]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = []

        with httpx.Client(timeout=15.0, headers=_HEADERS) as client:
            slugs = self._fetch_slugs(client, now)
            for slug, date_str in slugs:
                try:
                    event = self._fetch_event(client, slug, date_str)
                    if event and event.start_datetime >= now:
                        events.append(event)
                except Exception as e:
                    print(f"Warning: skipped {slug} — {e}")
                time.sleep(0.3)

        return sorted(events, key=lambda e: e.start_datetime)

    # --- Stage 1: calendar listing ---

    def _fetch_slugs(self, client, now: datetime) -> list[tuple[str, str]]:
        resp = client.get(_CALENDAR_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        for a in soup.find_all("a", class_="event"):
            href = a.get("href", "")
            if not href.startswith("/kalender/"):
                continue
            slug = href.removeprefix("/kalender/")
            h3 = a.find("h3")
            if not h3 or not h3.contents:
                continue
            date_str = str(h3.contents[0]).strip()
            # Pre-filter: skip dates already in the past
            date = _parse_date(date_str)
            if date and date.date() < now.date():
                continue
            results.append((slug, date_str))
        return results

    # --- Stage 2: individual event page ---

    def _fetch_event(self, client, slug: str, date_str: str) -> Event | None:
        url = f"{_BASE}/kalender/{slug}"
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        if h1 is None:
            return None
        title = h1.get_text(strip=True)
        if "aflyst" in title.lower():
            return None

        concert_time = _get_table_value(soup, "Koncertstart")
        doors_str = _get_table_value(soup, "Dørene åbner")
        price_str = _get_table_value(soup, "Pris")

        start_dt = _build_datetime(date_str, concert_time)
        if start_dt is None:
            return None

        ticket_link = soup.find("a", class_="buy-button")
        ticket_url = ticket_link["href"] if ticket_link else None

        og_image = soup.find("meta", property="og:image")
        image_url = og_image["content"] if og_image else None

        return Event(
            external_id=slug,
            title=title,
            venue=self.venue_name,
            city=self.city_slug,
            event_url=url,
            ticket_url=ticket_url,
            source="html",
            start_datetime=start_dt,
            doors_open=_parse_time(doors_str),
            price=price_str,
            image_url=image_url,
        )


# --- Helpers ---

def _parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None


def _parse_time(time_str: str | None) -> Time | None:
    if not time_str:
        return None
    try:
        t = datetime.strptime(time_str.strip(), "%H:%M")
        return t.time()
    except ValueError:
        return None


def _build_datetime(date_str: str, time_str: str | None) -> datetime | None:
    date = _parse_date(date_str)
    if date is None:
        return None
    t = _parse_time(time_str)
    if t:
        return date.replace(hour=t.hour, minute=t.minute)
    return date


def _get_table_value(soup: BeautifulSoup, label: str) -> str | None:
    for row in soup.find_all("div", class_="table-row"):
        cells = row.find_all("div", class_="cell")
        if len(cells) >= 2 and label.lower() in cells[0].get_text(strip=True).lower():
            return cells[1].get_text(strip=True)
    return None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching events...", file=sys.stderr)
    scraper = TrainScraper()
    events = scraper.fetch_events()
    print(f"Done. {len(events)} upcoming events.", file=sys.stderr)
    print(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False))
