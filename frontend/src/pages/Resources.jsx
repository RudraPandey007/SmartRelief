import React, { useState } from "react";
import useVillages from "../hooks/useVillages";
import useDashboardOverview from "../hooks/useDashboardOverview";
import useGeneratePlan from "../hooks/useGeneratePlan";
import {
  Warehouse, Loader2, CircleAlert, CheckCircle2,
  AlertTriangle, ChevronDown, Hospital, Droplets,
} from "lucide-react";

function scoreLabel(s) {
  if (s == null) return "N/A";
  if (s >= 0.8) return "Good";
  if (s >= 0.5) return "Moderate";
  return "Limited";
}

export default function Resources() {
  const { overview, loading: oLoading } = useDashboardOverview();
  const { villages, loading: vLoading } = useVillages();
  const { plan, loading: pLoading, generatePlan } = useGeneratePlan();
  const [selected, setSelected] = useState("V001");

  const handleSearch = () => { if (selected) generatePlan(selected); };

  const healthcareCount = villages.filter(v => v.has_healthcare).length;
  const waterCount = villages.filter(v => v.has_water_supply).length;

  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Resources</h2><p>Shelter capacity, healthcare access and essential services</p></div>
      </div>

      {oLoading && <div className="page-loading"><Loader2 size={24} className="spin" /><span>Loading…</span></div>}

      {overview && (
        <div className="stat-cards">
          <div className="stat-card">
            <div className="stat-icon green"><Warehouse size={20} /></div>
            <div><span>Total Shelters</span><strong>{overview.total_shelters}</strong></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon orange"><Warehouse size={20} /></div>
            <div><span>Total Capacity</span><strong>{overview.total_shelter_capacity.toLocaleString()}</strong></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><CheckCircle2 size={20} /></div>
            <div><span>Available Beds</span><strong>{overview.available_shelter_capacity.toLocaleString()}</strong><small>{Math.round((overview.available_shelter_capacity / overview.total_shelter_capacity) * 100)}% free</small></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon purple"><Hospital size={20} /></div>
            <div><span>Villages with Healthcare</span><strong>{healthcareCount}/{villages.length}</strong></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><Droplets size={20} /></div>
            <div><span>Villages with Water Supply</span><strong>{waterCount}/{villages.length}</strong></div>
          </div>
        </div>
      )}

      {/* Shelter details from plan */}
      <div className="planner-controls" style={{ marginTop: 16 }}>
        <div className="select-group">
          <label>Show shelters near</label>
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
          {pLoading ? <><Loader2 size={16} className="spin" /> Loading…</> : <><Warehouse size={16} /> Find Shelters</>}
        </button>
      </div>

      {pLoading && <div className="page-loading"><Loader2 size={24} className="spin" /><span>Searching shelters…</span></div>}

      {plan && !pLoading && (
        <div className="dest-grid">
          {plan.ranked_destinations.map(d => (
            <div key={d.destination_id} className="dest-card card available">
              <div className="dest-header">
                <div className="dest-icon"><Warehouse size={18} /></div>
                <div>
                  <b>{d.destination_name}</b>
                  <span>{d.destination_id}</span>
                </div>
                <span className="score-badge">{Math.round(d.weighted_total * 100)}/100</span>
              </div>
              <div className="dest-details">
                <div><span>Total Capacity</span><b>{d.total_capacity?.toLocaleString() || "—"}</b></div>
                <div><span>Available</span><b>{d.available_capacity?.toLocaleString() || "—"}</b></div>
                <div><span>Healthcare</span><b>{scoreLabel(d.healthcare_score)}</b></div>
                <div><span>Water</span><b>{scoreLabel(d.water_score)}</b></div>
                <div><span>Distance</span><b>{d.route_distance_km} km</b></div>
                {d.families_allocated > 0 && <div><span>Allocated</span><b>{d.families_allocated} families</b></div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
