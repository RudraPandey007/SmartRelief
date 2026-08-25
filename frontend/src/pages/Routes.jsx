import React, { useState } from "react";
import useVillages from "../hooks/useVillages";
import useGeneratePlan from "../hooks/useGeneratePlan";
import {
  Navigation, Loader2, ChevronDown, CheckCircle2,
  AlertTriangle, CircleAlert, MapPinned,
} from "lucide-react";

function routeStatusColor(s) {
  if (s === "blocked") return "red";
  if (s === "degraded") return "orange";
  return "green";
}

function scoreLabel(s) {
  if (s == null) return "N/A";
  if (s >= 0.8) return "Good";
  if (s >= 0.5) return "Moderate";
  return "Poor";
}

export default function Routes() {
  const { villages, loading: vLoading } = useVillages();
  const { plan, loading: pLoading, generatePlan } = useGeneratePlan();
  const [selected, setSelected] = useState("V001");

  const handleSearch = () => { if (selected) generatePlan(selected); };

  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Routes</h2><p>Evacuation route safety and accessibility monitoring</p></div>
      </div>

      <div className="planner-controls">
        <div className="select-group">
          <label>Routes from</label>
          <div className="custom-select">
            <select value={selected} onChange={e => setSelected(e.target.value)}>
              {villages.map(v => (
                <option key={v.id} value={v.id}>{v.name} ({v.id})</option>
              ))}
            </select>
            <ChevronDown size={16} />
          </div>
        </div>
        <button className="primary-btn" onClick={handleSearch} disabled={pLoading || !selected}>
          {pLoading ? <><Loader2 size={16} className="spin" /> Loading…</> : <><Navigation size={16} /> View Routes</>}
        </button>
      </div>

      {!plan && !pLoading && (
        <div className="page-empty">
          <Navigation size={40} />
          <span>Select a source village to view evacuation routes</span>
        </div>
      )}

      {pLoading && <div className="page-loading"><Loader2 size={24} className="spin" /><span>Loading routes…</span></div>}

      {plan && !pLoading && (
        <div className="routes-section">
          {/* All ranked routes */}
          <div className="card">
            <div className="card-head"><div><h2>Available Routes</h2><p>{plan.ranked_destinations.length} routes from {plan.village_name}</p></div></div>
            <div className="routes-list">
              {plan.ranked_destinations.map(d => (
                <div key={d.destination_id} className="route-row">
                  <div className="route-from-to">
                    <MapPinned size={14} />
                    <span className="route-from">{plan.village_name}</span>
                    <span className="route-arrow">→</span>
                    <span className="route-to">{d.destination_name}</span>
                  </div>
                  <div className="route-info">
                    <span>{d.route_distance_km} km</span>
                    <span>{d.route_time_min} min</span>
                    <span className={`route-status ${routeStatusColor(d.route_status)}`}>
                      {d.route_status === "blocked" ? <AlertTriangle size={11} /> : <CheckCircle2 size={11} />}
                      {d.route_status}
                    </span>
                    <span className="route-safety">{scoreLabel(d.route_safety_score)} ({Math.round(d.route_safety_score * 100)}%)</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Blocked routes from rejected */}
          {plan.rejected_destinations.filter(d => d.rejection_reasons?.some(r => r.toLowerCase().includes("route") || r.toLowerCase().includes("blocked"))).length > 0 && (
            <div className="card">
              <div className="card-head"><div><h2>Blocked / Unavailable Routes</h2><p>Routes excluded due to safety constraints</p></div></div>
              <div className="routes-list">
                {plan.rejected_destinations
                  .filter(d => d.rejection_reasons?.some(r => r.toLowerCase().includes("route") || r.toLowerCase().includes("blocked")))
                  .map(d => (
                    <div key={d.destination_id} className="route-row blocked">
                      <div className="route-from-to">
                        <AlertTriangle size={14} />
                        <span className="route-from">{plan.village_name}</span>
                        <span className="route-arrow">✗</span>
                        <span className="route-to">{d.destination_name}</span>
                      </div>
                      <div className="route-info">
                        <span className="route-status red"><AlertTriangle size={11} /> blocked</span>
                        <span className="route-reason">{d.rejection_reasons.join("; ")}</span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
