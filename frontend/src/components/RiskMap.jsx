/**
 * RiskMap — real interactive Leaflet map using MapTiler tiles.
 *
 * Layers:
 *   - Source village (red marker)
 *   - Ranked destinations (green/yellow by score)
 *   - Rejected destinations (grey marker)
 *   - Route polyline (source → top-ranked destination)
 *
 * Each layer can be toggled on/off via a checkbox panel overlay.
 */
import React, { useMemo, useState, useCallback, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, LayerGroup, useMap } from "react-leaflet";
import L from "leaflet";

// --- Fix Vite marker-icon bug (known Leaflet issue) ---
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

// --- Custom marker icons using SVG data URIs (reliable rendering) ---
function createSvgIcon(svgContent, size = 28) {
  return L.divIcon({
    className: "",  // empty class — avoid CSS conflicts
    html: svgContent,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

function makeCircleSvg(color, size, borderColor = "#fff") {
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
    <circle cx="${size/2}" cy="${size/2}" r="${size/2 - 3}" fill="${color}" stroke="${borderColor}" stroke-width="3"/>
    <circle cx="${size/2}" cy="${size/2}" r="${size/2 - 3}" fill="none" stroke="rgba(0,0,0,0.15)" stroke-width="1" transform="translate(1,2)"/>
  </svg>`;
}

// Source: red with white border, slightly larger
const ICON_SOURCE = createSvgIcon(
  `<svg width="36" height="42" viewBox="0 0 36 42" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="ds" x="-20%" y="-10%" width="140%" height="130%">
        <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.3"/>
      </filter>
    </defs>
    <path d="M18 38 C18 38 4 24 4 14 A14 14 0 1 1 32 14 C32 24 18 38 18 38Z" fill="#dc2626" stroke="#fff" stroke-width="3" filter="url(#ds)"/>
    <text x="18" y="18" text-anchor="middle" dominant-baseline="middle" font-size="14" font-weight="bold" fill="#fff">S</text>
  </svg>`,
  36
);

// Top recommendation: green pin
function makeDestIcon(color, label, size = 30) {
  return createSvgIcon(
    `<svg width="${size}" height="${size + 8}" viewBox="0 0 ${size} ${size + 8}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="dm${label}" x="-20%" y="-10%" width="140%" height="130%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.25"/>
        </filter>
      </defs>
      <circle cx="${size/2}" cy="${size/2}" r="${size/2 - 3}" fill="${color}" stroke="#fff" stroke-width="3" filter="url(#dm${label})"/>
      <text x="${size/2}" y="${size/2 + 1}" text-anchor="middle" dominant-baseline="middle" font-size="12" font-weight="bold" fill="#fff">${label}</text>
    </svg>`,
    size
  );
}

const ICON_TOP = makeDestIcon("#16a34a", "★", 32);      // Green star for #1
const ICON_GOOD = makeDestIcon("#2563eb", "", 26);        // Blue for good
const ICON_FAIR = makeDestIcon("#ca8a04", "", 24);        // Yellow for fair
const ICON_REJECTED = makeDestIcon("#9ca3af", "✕", 22);  // Grey X for rejected

// --- MapTiler key from env ---
const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_API_KEY;

// --- Helper: score to label ---
function scoreLabel(score) {
  if (score == null) return "N/A";
  if (score >= 0.8) return "Good";
  if (score >= 0.5) return "Moderate";
  return "Limited";
}

// --- Helper: score to color class ---
function scoreColorClass(score) {
  if (score == null) return "";
  if (score >= 0.7) return "text-green";
  if (score >= 0.4) return "text-orange";
  return "text-red";
}

// --- Helper: risk classification to display ---
function riskDisplay(cls) {
  if (!cls) return "N/A";
  return cls.charAt(0).toUpperCase() + cls.slice(1);
}

// --- Fly-to helper component ---
function FlyTo({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) {
      map.flyTo(position, map.getZoom(), { duration: 1.2 });
    }
  }, [position, map]);
  return null;
}

// --- Layer toggle panel ---
function LayerTogglePanel({ layers, setLayers }) {
  const toggle = useCallback((key) => {
    setLayers((prev) => ({ ...prev, [key]: { ...prev[key], visible: !prev[key].visible } }));
  }, [setLayers]);

  return (
    <div className="map-layer-panel">
      <b>Layers</b>
      {Object.entries(layers).map(([key, { label, visible }]) => (
        <label key={key} className="map-layer-item">
          <input
            type="checkbox"
            checked={visible}
            onChange={() => toggle(key)}
          />
          <span>{label}</span>
        </label>
      ))}
    </div>
  );
}

// --- Main RiskMap component ---
export default function RiskMap({ plan }) {
  // Layer visibility state
  const [layers, setLayers] = useState({
    source: { label: "Source Village", visible: true },
    ranked: { label: "Ranked Destinations", visible: true },
    route: { label: "Route Line", visible: true },
    rejected: { label: "Rejected Destinations", visible: false },
  });

  // Source village coordinates
  const sourcePos = plan ? [plan.latitude, plan.longitude] : null;

  // Map center: source village or default
  const center = sourcePos || [27.48, 94.58]; // Dhemaji fallback

  // Ranked destinations with coordinates
  const rankedDests = useMemo(() => {
    if (!plan?.ranked_destinations) return [];
    return plan.ranked_destinations.filter(
      (d) => d.latitude && d.longitude && (d.latitude !== 0 || d.longitude !== 0)
    );
  }, [plan]);

  // Rejected destinations with coordinates
  const rejectedDests = useMemo(() => {
    if (!plan?.rejected_destinations) return [];
    return plan.rejected_destinations.filter(
      (d) => d.latitude && d.longitude && (d.latitude !== 0 || d.longitude !== 0)
    );
  }, [plan]);

  // Route polyline: source → top destination
  const routeLine = useMemo(() => {
    if (!sourcePos || rankedDests.length === 0) return null;
    const topDest = rankedDests[0];
    return [sourcePos, [topDest.latitude, topDest.longitude]];
  }, [sourcePos, rankedDests]);

  // Destination icon based on rank/score
  function destIcon(dest) {
    if (dest.rank === 1) return ICON_TOP;
    if (dest.weighted_total >= 0.65) return ICON_GOOD;
    return ICON_FAIR;
  }

  // Missing MapTiler key warning
  if (!MAPTILER_KEY || MAPTILER_KEY === "replace_with_your_maptiler_key_here") {
    console.warn(
      "[RiskMap] VITE_MAPTILER_API_KEY is not set. Map tiles will not load. " +
      "Add it to frontend/.env.local"
    );
  }

  if (!plan) {
    return <div className="map-loading">Loading map data…</div>;
  }

  return (
    <div className="map-wrap">
      <MapContainer
        center={center}
        zoom={9}
        scrollWheelZoom={true}
        style={{ width: "100%", height: "100%", borderRadius: "12px" }}
      >
        {/* Tile layer — MapTiler */}
        <TileLayer
          url={`https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${MAPTILER_KEY || ""}`}
          attribution='&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
        />

        {/* Fly to source when plan changes */}
        {sourcePos && <FlyTo position={sourcePos} />}

        {/* Source village marker */}
        {layers.source.visible && sourcePos && (
          <LayerGroup>
            <Marker position={sourcePos} icon={ICON_SOURCE}>
              <Popup>
                <div className="map-popup">
                  <h4>{plan.village_name}</h4>
                  <span className="popup-badge popup-badge-red">SOURCE</span>
                  <p><b>Risk:</b> {riskDisplay(plan.risk_classification)}</p>
                  <p><b>Hazard Score:</b> {Math.round(plan.hazard_score * 100)}%</p>
                  <p><b>Affected Families:</b> {plan.affected_families.toLocaleString()}</p>
                  <p><b>Population:</b> {plan.population.toLocaleString()}</p>
                </div>
              </Popup>
            </Marker>
          </LayerGroup>
        )}

        {/* Ranked destination markers */}
        {layers.ranked.visible && (
          <LayerGroup>
            {rankedDests.map((dest) => (
              <Marker
                key={dest.destination_id}
                position={[dest.latitude, dest.longitude]}
                icon={destIcon(dest)}
              >
                <Popup>
                  <div className="map-popup">
                    <h4>{dest.destination_name}</h4>
                    {dest.rank === 1 && (
                      <span className="popup-badge popup-badge-green">★ RECOMMENDED</span>
                    )}
                    <p><b>Score:</b> {Math.round(dest.weighted_total * 100)}/100</p>
                    <p><b>Capacity:</b> {dest.available_capacity.toLocaleString()} families</p>
                    <p><b>Healthcare:</b> <span className={scoreColorClass(dest.healthcare_score)}>{scoreLabel(dest.healthcare_score)}</span></p>
                    <p><b>Water:</b> <span className={scoreColorClass(dest.water_score)}>{scoreLabel(dest.water_score)}</span></p>
                    <p><b>Route Safety:</b> <span className={scoreColorClass(dest.route_safety_score)}>{scoreLabel(dest.route_safety_score)}</span></p>
                    <p><b>Distance:</b> {dest.route_distance_km} km · {dest.route_time_min} min</p>
                    {dest.families_allocated > 0 && (
                      <p><b>Allocated:</b> {dest.families_allocated.toLocaleString()} families</p>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}
          </LayerGroup>
        )}

        {/* Rejected destination markers */}
        {layers.rejected.visible && (
          <LayerGroup>
            {rejectedDests.map((dest) => (
              <Marker
                key={dest.destination_id}
                position={[dest.latitude, dest.longitude]}
                icon={ICON_REJECTED}
              >
                <Popup>
                  <div className="map-popup">
                    <h4>{dest.destination_name}</h4>
                    <span className="popup-badge popup-badge-grey">REJECTED</span>
                    {dest.rejection_reasons?.map((reason, i) => (
                      <p key={i}>⚠️ {reason}</p>
                    ))}
                  </div>
                </Popup>
              </Marker>
            ))}
          </LayerGroup>
        )}

        {/* Route polyline */}
        {layers.route.visible && routeLine && (
          <Polyline
            positions={routeLine}
            pathOptions={{
              color: "#2563eb",
              weight: 3,
              opacity: 0.8,
              dashArray: "8 6",
            }}
          />
        )}
      </MapContainer>

      {/* Layer toggle panel */}
      <LayerTogglePanel layers={layers} setLayers={setLayers} />

      {/* Map legend */}
      <div className="map-legend">
        <b>Legend</b>
        <span><i className="dot" style={{ background: "#dc2626" }} /> Source Village</span>
        <span><i className="dot" style={{ background: "#16a34a" }} /> Top Recommendation</span>
        <span><i className="dot" style={{ background: "#2563eb" }} /> Good Candidate</span>
        <span><i className="dot" style={{ background: "#ca8a04" }} /> Fair Candidate</span>
        <span><i className="dot" style={{ background: "#9ca3af" }} /> Rejected</span>
        <span className="legend-route">- - Route Line (direct)</span>
      </div>
    </div>
  );
}
