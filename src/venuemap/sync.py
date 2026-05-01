"""
Entry point for running all scrapers and persisting results to the database.

Usage:
    uv run python -m venuemap.sync
"""

import sys
from datetime import datetime, timezone

from venuemap.db.session import SessionLocal
from venuemap.db.upsert import get_or_create_venue, record_scrape_run, upsert_events
from venuemap.scrapers.voxhall import VoxhallScraper


def sync_voxhall(session) -> None:
    scraper = VoxhallScraper()
    venue = get_or_create_venue(
        session,
        venue_slug="voxhall-aarhus",
        venue_name="Voxhall",
        city_slug="aarhus",
        city_name="Aarhus",
    )

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    error = None
    events = []

    try:
        print("  Fetching events from Voxhall...", flush=True)
        events = scraper.fetch_events()
        print(f"  Fetched {len(events)} upcoming events.", flush=True)
    except Exception as e:
        error = str(e)
        print(f"  ERROR: {e}", file=sys.stderr)

    result = {"new": 0, "updated": 0, "total_upcoming": 0}
    if events:
        result = upsert_events(session, events, venue)

    record_scrape_run(
        session,
        venue=venue,
        started_at=started_at,
        events_found=len(events),
        new_count=result["new"],
        updated_count=result["updated"],
        error=error,
    )

    print(
        f"  Done — {result['total_upcoming']} upcoming events: "
        f"{result['new']} new, {result['updated']} updated."
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== VenueMap sync ===")
    with SessionLocal() as session:
        print("Voxhall:")
        sync_voxhall(session)
    print("=== Sync complete ===")
