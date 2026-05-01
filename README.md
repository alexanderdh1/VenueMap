# VenueMap

*Discover live music at small or large venues in your city, on a map.*

## What it is

A web application that shows music venues in a city, presents them on an interactive map, and helps users discover relevant shows and artists in their area.

Starting in one city with the eventual goal of supporting multiple cities, added at a later time.

## Core functionality

The platform aggregates event data from a curated list of venue websites by scraping them on a schedule. Each event is normalized to a common format (venue, artist(s), date/time, ticket link, price if available) and enriched with artist metadata pulled from external APIs (Spotify, Last.fm, MusicBrainz) including genre tags and similar artists.

The primary user interface is a map. Users pan around a city and see pins for venues with upcoming shows. Clicking a venue opens a panel with its upcoming events, a description, and user ratings. Filtering controls let users narrow by date range, genre, and distance from a point.

Authenticated users can connect a Spotify account so the platform can pull their listening history. This drives a personalization layer: events featuring artists the user listens to (or artists similar to those) are highlighted and ranked higher. Users can save venues, mark events as "going," rate venues or events, and maintain a personal concert history.

A health-monitoring system tracks scraper performance. When a venue website changes structure and a scraper breaks, the system detects the drop in event volume or parser failure and alerts the maintainer. This is operationally critical because scrapers will break constantly.

## Engineering scope

Caching is a first-class concern at multiple layers: scraped HTML cached by URL with TTL, parsed events cached until the next scheduled scrape, geocoding results cached indefinitely, and external API responses cached aggressively to respect rate limits and reduce cost.

A job queue handles all asynchronous work: scheduled scrapes, geocoding of new venues, artist enrichment, user notifications. Structured logs record every scrape run, every API call, and every parse error, queryable for debugging and health monitoring.

The data model treats city as a first-class concept from day one even though only one city will be supported initially. 

## Out of scope (for v1)

Native mobile apps, social/friend features, ticket purchasing integration, AI-based recommendations, event creation by venue owners, and multi-city support are all explicitly deferred. The v1 goal is a working aggregator for 5–10 venues with a map interface, basic filtering, user accounts, and Spotify-driven personalization. Everything else is v2+ and depends on whether v1 is actually useful.

## Open questions

- Tech stack choice (backend language/framework, frontend framework).
- Hosting target.
- Initial venue list.
- Approach to system architecture.
