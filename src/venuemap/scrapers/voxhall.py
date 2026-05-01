import json
import re
from datetime import datetime, time, timezone
from html import unescape

import httpx
from bs4 import BeautifulSoup

from venuemap.models.event import Event

_BASE_URL = "https://voxhall.dk/wp-json/wp/v2"
_VENUE_NAME = "Voxhall"
_CITY = "aarhus"
_START_DATE_RE = re.compile(r'itemprop="startDate"[^>]+(?:datetime|content)="([^"]+)"')


class VoxhallScraper:
    venue_id = "voxhall-aarhus"
    venue_name = _VENUE_NAME
    city = _CITY

    def fetch_events(self) -> list[Event]:
        raw = self._fetch_all_raw()
        events = []
        for item in raw:
            try:
                event = self._parse_event(item)
                if event is not None:
                    events.append(event)
            except Exception as e:
                print(f"Warning: skipped event {item.get('id')} — {e}")
        return events

    # --- Fetching ---

    def _fetch_all_raw(self) -> list[dict]:
        results = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        seen_future = False
        page = 1
        with httpx.Client(timeout=15.0) as client:
            while True:
                resp = client.get(
                    f"{_BASE_URL}/voxhall-event",
                    params={"per_page": 100, "page": page, "_embed": 1},
                )
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break
                results.extend(batch)
                dates = [self._quick_start_dt(item) for item in batch]
                future_on_page = [dt for dt in dates if dt is not None and dt >= now]
                if future_on_page:
                    seen_future = True
                elif seen_future:
                    # No future events on this page, and we've already seen some — stop
                    break
                total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
                if page >= total_pages:
                    break
                page += 1
        return results

    def _quick_start_dt(self, item: dict) -> datetime | None:
        html = item.get("content", {}).get("rendered", "")
        m = _START_DATE_RE.search(html)
        if not m:
            return None
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    # --- Top-level event parsing ---

    def _parse_event(self, item: dict) -> Event | None:
        soup = BeautifulSoup(item["content"]["rendered"], "lxml")

        start_dt = self._parse_datetime(soup, "startDate")
        if start_dt is None:
            return None
        if start_dt < datetime.now(timezone.utc).replace(tzinfo=None):
            return None

        return Event(
            external_id=str(item["id"]),
            title=unescape(item["title"]["rendered"]),
            venue=_VENUE_NAME,
            city=_CITY,
            event_url=item["link"],
            source="wp_api",
            start_datetime=start_dt,
            end_datetime=self._parse_datetime(soup, "endDate"),
            doors_open=self._parse_door_time(soup),
            genres=self._extract_genres(item),
            ticket_url=self._parse_ticket_url(soup),
            ticket_status=self._parse_ticket_status(soup),
            price=self._parse_price(soup),
            image_url=self._extract_image(item),
        )

    # --- HTML field parsers ---

    def _parse_datetime(self, soup: BeautifulSoup, itemprop: str) -> datetime | None:
        tag = soup.find(attrs={"itemprop": itemprop})
        if tag is None:
            return None
        raw = tag.get("datetime") or tag.get("content")
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def _parse_door_time(self, soup: BeautifulSoup) -> time | None:
        tag = soup.find(attrs={"itemprop": "doorTime"})
        if tag is None:
            return None
        # content attribute is formatted like "18.00"
        raw = tag.get("content", "")
        try:
            hour, minute = raw.replace(".", ":").split(":")
            return time(int(hour), int(minute))
        except (ValueError, AttributeError):
            return None

    def _parse_ticket_url(self, soup: BeautifulSoup) -> str | None:
        bar = soup.find(attrs={"event-hero-ticket-bar": True})
        if bar is None:
            return None
        link = bar.find("a", class_=lambda c: c and "btn" in c)
        return link["href"] if link else None

    def _parse_ticket_status(self, soup: BeautifulSoup) -> str | None:
        bar = soup.find(attrs={"event-hero-ticket-bar": True})
        if bar is None:
            return None
        disabled_btn = bar.find("button", attrs={"disabled": True})
        if disabled_btn:
            return disabled_btn.get_text(strip=True)
        link = bar.find("a", class_=lambda c: c and "btn" in c)
        if link:
            return "on_sale"
        return None

    def _parse_price(self, soup: BeautifulSoup) -> str | None:
        info = soup.find("section", class_=lambda c: c and "block-event-information" in c)
        if info is None:
            return None
        text = info.get_text(separator="\n")
        match = re.search(r"(\d[\d.,\- ]*\s*kr\.?|free|gratis)", text, re.IGNORECASE)
        return match.group(0).strip() if match else None

    # --- Embedded data helpers ---

    def _extract_genres(self, item: dict) -> list[str]:
        try:
            for term_group in item["_embedded"]["wp:term"]:
                if term_group and term_group[0].get("taxonomy") == "voxhall-event-genre":
                    return [t["name"] for t in term_group]
        except (KeyError, TypeError, IndexError):
            pass
        return []

    def _extract_image(self, item: dict) -> str | None:
        try:
            return item["_embedded"]["wp:featuredmedia"][0]["source_url"]
        except (KeyError, TypeError, IndexError):
            return None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching events...", file=sys.stderr)
    scraper = VoxhallScraper()
    events = scraper.fetch_events()
    print(f"Done. Parsing complete.", file=sys.stderr)
    print(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False))
    print(f"\nTotal: {len(events)} events")
