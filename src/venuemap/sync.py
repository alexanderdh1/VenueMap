"""
Entry point for running all scrapers and persisting results to the database.

Usage:
    uv run python -m venuemap.sync
"""

import sys
from datetime import datetime, timezone

from venuemap.db.session import SessionLocal
from venuemap.db.upsert import get_or_create_venue, record_scrape_run, upsert_events
from venuemap.scrapers.base import Scraper
from venuemap.scrapers.voxhall import VoxhallScraper


def sync_venue(session, scraper: Scraper) -> None:
    venue = get_or_create_venue(
        session,
        venue_slug=scraper.venue_id,
        venue_name=scraper.venue_name,
        city_slug=scraper.city_slug,
        city_name=scraper.city_name,
        latitude=scraper.latitude,
        longitude=scraper.longitude,
    )

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    error = None
    events = []

    try:
        print(f"  Fetching events from {scraper.venue_name}...", flush=True)
        events = scraper.fetch_events()
        print(f"  Fetched {len(events)} upcoming events.", flush=True)
    except Exception as e:
        error = str(e)
        print(f"  ERROR: {e}", file=sys.stderr)

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
            f"  WARNING: scrape log could not be written\n"
            f"    venue:      {scraper.venue_name} ({scraper.venue_id})\n"
            f"    started_at: {started_at}\n"
            f"    failed_at:  {failed_at}\n"
            f"    duration:   {(failed_at - started_at).total_seconds():.1f}s\n"
            f"    reason:     {log_exc.__class__.__name__}: {log_exc}",
            file=sys.stderr,
        )

    print(
        f"  Done — {result['total_upcoming']} upcoming events: "
        f"{result['new']} new, {result['updated']} updated."
    )


SCRAPERS: list[Scraper] = [
    VoxhallScraper(),
]

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== VenueMap sync ===")
    with SessionLocal() as session:
        for scraper in SCRAPERS:
            print(f"{scraper.venue_name}:")
            sync_venue(session, scraper)
    print("=== Sync complete ===")
