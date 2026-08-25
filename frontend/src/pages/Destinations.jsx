import React, { useState } from "react";
import useVillages from "../hooks/useVillages";
import useGeneratePlan from "../hooks/useGeneratePlan";
import {
  House, Warehouse, Loader2, CircleAlert, CheckCircle2,
  AlertTriangle, ChevronDown, Hospital, Droplets,
} from "lucide-react";

function scoreLabel(s) {
  if (s == null) return "N/A";
  if (s >= 0.8) return "Good";
  if (s >= 0.5) return "Moderate";
  return "Limited";
}

function riskColor(r) {
  if (r >= 0.75) return "red";
  if (r >= 0.55) return "orange";
  if (r >= 0.35) return "yellow";
  return "green";
}

export default function Destinations() {
  const { villages, loading: vLoading } = useVillages();
  const { plan, loading: pLoading, generatePlan } = useGeneratePlan();
  const [selected, setSelected] = useState("V001");

  const handleSearch = () => { if (selected) generatePlan(selected); };

  const allDests = [
    ...(plan?.ranked_destinations || []),
    ...(plan?.rejected_destinations || []).map(d => ({ ...d, rejected: true })),
  ];

  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Destinations</h2><p>Available relocation destinations and shelter capacity</p></div>
      </div>

      <div className="planner-controls">
        <div className="select-group">
          <label>Search destinations from</label>
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
          {pLoading ? <><Loader2 size={16} className="spin" /> Searching…</> : <><House size={16} /> Search Destinations</>}
        </button>
      </div>

      {!plan && !pLoading && (
        <div className="page-empty">
          <House size={40} />
          <span>Select a source village and search to see available destinations</span>
        </div>
      )}

      {pLoading && <div className="page-loading"><Loader2 size={24} className="spin" /><span>Searching…</span></div>}

      {allDests.length > 0 && !pLoading && (
        <div className="dest-grid">
          {allDests.map(d => (
            <div key={d.destination_id} className={`dest-card card ${d.rejected ? "rejected" : "available"}`}>
              <div className="dest-header">
                <div className="dest-icon">
                  {d.rejected ? <AlertTriangle size={18} /> : <Warehouse size={18} />}
                </div>
                <div>
                  <b>{d.destination_name}</b>
                  <span>{d.destination_id} · {d.destination_type || "village"}</span>
                </div>
                {!d.rejected && <span className="score-badge">{Math.round(d.weighted_total * 100)}/100</span>}
                {d.rejected && <span className="rejected-badge">Rejected</span>}
              </div>
              <div className="dest-details">
                <div><span>Healthcare</span><b>{scoreLabel(d.healthcare_score)}</b></div>
                <div><span>Water</span><b>{scoreLabel(d.water_score)}</b></div>
                <div><span>Route Safety</span><b>{scoreLabel(d.route_safety_score)}</b></div>
                <div><span>Distance</span><b>{d.route_distance_km || "—"} km</b></div>
                {d.available_capacity != null && <div><span>Capacity</span><b>{d.available_capacity.toLocaleString()}</b></div>}
                {d.families_allocated > 0 && <div><span>Allocated</span><b>{d.families_allocated} families</b></div>}
              </div>
              {d.rejected && d.rejection_reasons && (
                <div className="dest-rejection">
                  <AlertTriangle size={12} /> {d.rejection_reasons.join("; ")}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
