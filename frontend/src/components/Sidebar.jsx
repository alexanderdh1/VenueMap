import { useEffect, useState } from "react";
import { fetchEvents } from "../api";
import EventCard from "./EventCard";

export default function Sidebar({ venue, onClose }) {
  const [events, setEvents] = useState([]);
  const [hasMore, setHasMore] = useState(false);
  const [showingAll, setShowingAll] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!venue) return;
    setEvents([]);
    setShowingAll(false);
    setLoading(true);
    fetchEvents(venue.slug)
      .then((data) => {
        setEvents(data.events);
        setHasMore(data.has_events_beyond_window);
      })
      .finally(() => setLoading(false));
  }, [venue]);

  function handleShowMore() {
    setLoading(true);
    fetchEvents(venue.slug, { dateTo: "2099-12-31T00:00:00" })
      .then((data) => {
        setEvents(data.events);
        setHasMore(false);
        setShowingAll(true);
      })
      .finally(() => setLoading(false));
  }

  if (!venue) return <div className="sidebar sidebar--empty" />;

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>{venue.name}</h2>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      <div className="sidebar-city">{venue.city}</div>

      {loading && <div className="sidebar-loading">Henter events…</div>}

      {!loading && events.length === 0 && (
        <div className="sidebar-empty">Ingen kommende events</div>
      )}

      <div className="event-list">
        {events.map((e) => (
          <EventCard key={e.id} event={e} />
        ))}
      </div>

      {hasMore && !loading && (
        <button className="show-more-btn" onClick={handleShowMore}>
          Vis alle events
        </button>
      )}

      {showingAll && (
        <div className="sidebar-all-shown">Alle kommende events vist</div>
      )}
    </div>
  );
}
