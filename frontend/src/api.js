const BASE = "http://localhost:8000/api";

export async function fetchVenues({ latMin, latMax, lngMin, lngMax } = {}) {
  const params = new URLSearchParams();
  if (latMin != null) {
    params.set("lat_min", latMin);
    params.set("lat_max", latMax);
    params.set("lng_min", lngMin);
    params.set("lng_max", lngMax);
  }
  const res = await fetch(`${BASE}/venues?${params}`);
  if (!res.ok) throw new Error("Failed to fetch venues");
  return res.json();
}

export async function fetchEvents(venueSlug, { dateTo } = {}) {
  const params = new URLSearchParams({ venue: venueSlug });
  if (dateTo) params.set("date_to", dateTo);
  const res = await fetch(`${BASE}/events?${params}`);
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}
