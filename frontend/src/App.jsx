import { useState } from "react";
import VenueMap from "./components/VenueMap";
import Sidebar from "./components/Sidebar";
import "./App.css";

export default function App() {
  const [selectedVenue, setSelectedVenue] = useState(null);

  return (
    <div className="app">
      <VenueMap onVenueSelect={setSelectedVenue} />
      {selectedVenue && (
        <Sidebar venue={selectedVenue} onClose={() => setSelectedVenue(null)} />
      )}
    </div>
  );
}
