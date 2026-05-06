import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.markercluster";
import { fetchVenues } from "../api";

const TILE_URL =
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTR =
  '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>';

const DEFAULT_CENTER = [20, 0];
const DEFAULT_ZOOM = 3;

export default function VenueMap({ onVenueSelect }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const clusterRef = useRef(null);
  const debounceRef = useRef(null);
  const [located, setLocated] = useState(false);
  const [apiError, setApiError] = useState(false);

  useEffect(() => {
    if (mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      zoomControl: true,
    });

    L.tileLayer(TILE_URL, { attribution: TILE_ATTR, maxZoom: 19 }).addTo(map);

    const cluster = L.markerClusterGroup();
    map.addLayer(cluster);

    clusterRef.current = cluster;
    mapRef.current = map;

    // Geolocation — center map on user's position
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => {
          if (mapRef.current !== map) return;
          map.setView([coords.latitude, coords.longitude], 12);
          setLocated(true);
        },
        () => {
          // Permission denied or unavailable — stay at default view
        }
      );
    }

    map.on("moveend", () => loadVenues(map, cluster));
    loadVenues(map, cluster);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  function loadVenues(map, cluster) {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const b = map.getBounds();
      fetchVenues({
        latMin: b.getSouth(),
        latMax: b.getNorth(),
        lngMin: b.getWest(),
        lngMax: b.getEast(),
      }).then((venues) => {
        setApiError(false);
        cluster.clearLayers();
        venues.forEach((venue) => {
          if (venue.latitude == null || venue.longitude == null) return;
          const marker = L.marker([venue.latitude, venue.longitude]);
          marker.on("click", () => onVenueSelect(venue));
          marker.bindTooltip(venue.name, { permanent: false, direction: "top" });
          cluster.addLayer(marker);
        });
      }).catch(() => setApiError(true));
    }, 300);
  }

  return (
    <div style={{ position: "relative", flex: 1, height: "100%" }}>
      <div ref={containerRef} className="map-container" />
      {apiError && (
        <div className="map-error">Kunne ikke forbinde til API</div>
      )}
    </div>
  );
}
