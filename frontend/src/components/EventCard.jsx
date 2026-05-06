export default function EventCard({ event }) {
  const date = new Date(event.start_datetime);
  const formatted = date.toLocaleDateString("da-DK", {
    day: "numeric",
    month: "short",
    year: "2-digit",
  });

  return (
    <a
      href={event.event_url}
      target="_blank"
      rel="noreferrer"
      className="event-card"
    >
      {event.image_url && (
        <img src={event.image_url} alt={event.title} className="event-image" />
      )}
      <div className="event-info">
        <div className="event-title">{event.title}</div>
        <div className="event-date">{formatted}</div>
        {event.genres.length > 0 && (
          <div className="event-genres">{event.genres.join(", ")}</div>
        )}
        {event.price && <div className="event-price">{event.price}</div>}
      </div>
    </a>
  );
}
