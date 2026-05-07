"""
Entry point for running all scrapers and persisting results to the database.

Usage:
    uv run python -m venuemap.sync
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from venuemap.db.session import SessionLocal
from venuemap.db.upsert import get_or_create_venue, record_scrape_run, upsert_events
from venuemap.scrapers.base import Scraper
from venuemap.scrapers.aarhus.erlings import ErlingsScraper
from venuemap.scrapers.aarhus.radar import RadarScraper
from venuemap.scrapers.aarhus.train import TrainScraper
from venuemap.scrapers.aarhus.volumevillage import VolumeVillageScraper
from venuemap.scrapers.aarhus.voxhall import VoxhallScraper


def sync_venue(scraper: Scraper) -> None:
    # Each call gets its own session so threads don't share state
    with SessionLocal() as session:
        venue = get_or_create_venue(
            session,
            venue_slug=scraper.venue_id,
            venue_name=scraper.venue_name,
            city_slug=scraper.city_slug,
            city_name=scraper.city_name,
            latitude=getattr(scraper, "latitude", None),
            longitude=getattr(scraper, "longitude", None),
            address=getattr(scraper, "address", None),
        )

        started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        error = None
        events = []

        try:
            print(f"  [{scraper.venue_name}] Fetching...", flush=True)
            events = scraper.fetch_events()
            print(f"  [{scraper.venue_name}] {len(events)} upcoming events.", flush=True)
        except Exception as e:
            error = str(e)
            print(f"  [{scraper.venue_name}] ERROR: {e}", file=sys.stderr, flush=True)

        result = {"new": 0, "updated": 0, "total_upcoming": 0}
        if events:
            result = upsert_events(session, events, venue)

        try:
            record_scrape_run(
                session,
                venue=venue,
                started_at=started_at,
                events_found=len(events),
                new_count=result["new"],
                updated_count=result["updated"],
                error=error,
            )
        except Exception as log_exc:
            failed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            print(
                f"  [{scraper.venue_name}] WARNING: scrape log could not be written\n"
                f"    started_at: {started_at}\n"
                f"    failed_at:  {failed_at}\n"
                f"    duration:   {(failed_at - started_at).total_seconds():.1f}s\n"
                f"    reason:     {log_exc.__class__.__name__}: {log_exc}",
                file=sys.stderr,
            )

        print(
            f"  [{scraper.venue_name}] Done — {result['total_upcoming']} upcoming: "
            f"{result['new']} new, {result['updated']} updated.",
            flush=True,
        )


SCRAPERS: list[Scraper] = [
    VoxhallScraper(),
    ErlingsScraper(),
    TrainScraper(),
    VolumeVillageScraper(),
    RadarScraper(),
]

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== VenueMap sync ===")

    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as executor:
        futures = {executor.submit(sync_venue, scraper): scraper for scraper in SCRAPERS}
        for future in as_completed(futures):
            scraper = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"  [{scraper.venue_name}] UNHANDLED ERROR: {e}", file=sys.stderr)

    print("=== Sync complete ===")
