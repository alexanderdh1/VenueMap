import json
import re
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from venuemap import http
from venuemap.models.event import Event
from venuemap.scrapers.base import Scraper

_BASE = "https://www.turkis.nu"
_OVERVIEW_URL = f"{_BASE}/events/koncert"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VenueMap/1.0)"}


class TurkisScraper(Scraper):
    venue_id = "turkis-aarhus"
    venue_name = "Turkis"
    city_slug = "aarhus"
    city_name = "Aarhus"
    address = "Vester Allé 15, Aarhus, Denmark"

    def fetch_events(self) -> list[Event]:
        with httpx.Client(timeout=15.0, headers=_HEADERS, follow_redirects=True) as client:
            resp = http.get(client, _OVERVIEW_URL)
            soup = BeautifulSoup(resp.text, "html.parser")

            events = []
            now = datetime.now()

            for link in self._extract_event_links(soup):
                try:
                    resp = http.get(client, link)
                    event = self._parse_event_page(resp.text, link)
                    if event and event.start_datetime >= now:
                        events.append(event)
                except Exception as e:
                    print(f"Warning: skipped {link} — {e}")

        return sorted(events, key=lambda e: e.start_datetime)

    def _extract_event_links(self, soup: BeautifulSoup) -> list[str]:
        links = []
        for card in soup.find_all("a", href=re.compile(r"/event/")):
            href = card.get("href")
            if href:
                links.append(urljoin(_BASE, href))
        return links

    def _parse_event_page(self, html: str, event_url: str) -> Event | None:
        soup = BeautifulSoup(html, "html.parser")

        title_elem = soup.find("h1")
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title:
            return None

        date_str = self._extract_text(soup, r"(\d{1,2}\.\d{1,2}\.\d{4})")
        if not date_str:
            return None

        start_dt = datetime.strptime(date_str, "%d.%m.%Y")

        image_url = None
        img = soup.find("img", {"alt": re.compile(".*", re.IGNORECASE)})
        if img and img.get("src"):
            image_url = urljoin(_BASE, img.get("src"))

        return Event(
            external_id=event_url.split("/")[-1],
            title=title,
            venue=self.venue_name,
            city=self.city_slug,
            event_url=event_url,
            source="html",
            start_datetime=start_dt,
            end_datetime=None,
            genres=[],
            image_url=image_url,
        )

    def _extract_text(self, soup: BeautifulSoup, pattern: str) -> str | None:
        text = soup.get_text()
        match = re.search(pattern, text)
        return match.group(1) if match else None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching events...", file=sys.stderr)
    scraper = TurkisScraper()
    events = scraper.fetch_events()
    print(f"Done. {len(events)} upcoming events.", file=sys.stderr)
    print(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False))
