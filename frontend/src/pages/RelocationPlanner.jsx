import React, { useState } from "react";
import useVillages from "../hooks/useVillages";
import useGeneratePlan from "../hooks/useGeneratePlan";
import {
  MapPinned, Loader2, CircleAlert, CheckCircle2, AlertTriangle,
  Warehouse, Route, Hospital, Droplets, ShieldAlert, Users,
  ArrowUpRight, ChevronDown,
} from "lucide-react";

function scoreLabel(s) {
  if (s == null) return "N/A";
  if (s >= 0.8) return "Good";
  if (s >= 0.5) return "Moderate";
  return "Limited";
}

function riskLabel(r) {
  if (r >= 0.75) return "Extreme";
  if (r >= 0.55) return "High";
  if (r >= 0.35) return "Moderate";
  return "Low";
}

function riskColor(r) {
  if (r >= 0.75) return "red";
  if (r >= 0.55) return "orange";
  if (r >= 0.35) return "yellow";
  return "green";
}

export default function RelocationPlanner() {
  const { villages, loading: vLoading } = useVillages();
  const { plan, loading: pLoading, error, generatePlan } = useGeneratePlan();
  const [selected, setSelected] = useState("V001");

  const handleGenerate = () => {
    if (selected) generatePlan(selected);
  };

  const topDest = plan?.ranked_destinations?.[0] || null;
  const allocatedDests = (plan?.ranked_destinations || []).filter(d => d.families_allocated > 0);
  const totalEval = (plan?.ranked_destinations?.length || 0) + (plan?.rejected_destinations?.length || 0);

  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Relocation Planner</h2><p>Generate optimized evacuation plans for any affected village</p></div>
      </div>

      {/* Village selector */}
      <div className="planner-controls">
        <div className="select-group">
          <label>Select Source Village</label>
          <div className="custom-select">
            <select value={selected} onChange={e => setSelected(e.target.value)}>
              {villages.map(v => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.id}) — Risk: {(v.river_flood_risk * 100).toFixed(0)}%, Pop: {v.population.toLocaleString()}
                </option>
              ))}
            </select>
            <ChevronDown size={16} />
          </div>
        </div>
        <button className="primary-btn" onClick={handleGenerate} disabled={pLoading || !selected}>
          {pLoading ? <><Loader2 size={16} className="spin" /> Generating…</> : <><MapPinned size={16} /> Generate Plan</>}
        </button>
      </div>

      {error && <div className="error-banner error-generic"><CircleAlert size={16} /><span>{error.message}</span></div>}

      {pLoading && (
        <div className="page-loading large">
          <Loader2 size={36} className="spin" />
          <span>Running decision pipeline…</span>
          <small>Hazard → Vulnerability → Candidates → Filtering → Optimization → Allocation</small>
        </div>
      )}

      {plan && !pLoading && (
        <div className="plan-results">
          {/* Source info */}
          <div className="plan-source card">
            <div className="card-head"><div><h2>Source Village</h2><p>{plan.village_name}, {plan.district}, {plan.state}</p></div>
              <span className={`risk-badge ${riskColor(plan.hazard_score)}`}>{plan.risk_classification?.toUpperCase()}</span></div>
            <div className="plan-stats">
              <div><Users size={16} /><span>Population</span><b>{plan.population.toLocaleString()}</b></div>
              <div><AlertTriangle size={16} /><span>Hazard Score</span><b>{(plan.hazard_score * 100).toFixed(1)}%</b></div>
              <div><ShieldAlert size={16} /><span>Combined Risk</span><b>{(plan.combined_risk * 100).toFixed(1)}%</b></div>
              <div><Users size={16} /><span>Affected Families</span><b>{plan.affected_families.toLocaleString()}</b></div>
            </div>
          </div>

          {/* Top recommendation */}
          {topDest && (
            <div className="plan-top card">
              <div className="card-head"><div><h2>Top Recommendation</h2><p>{topDest.destination_name} ({topDest.destination_id})</p></div>
                <div className="score-badge">{Math.round(topDest.weighted_total * 100)}/100</div></div>
              <div className="plan-stats">
                <div><Route size={16} /><span>Distance</span><b>{topDest.route_distance_km} km</b></div>
                <div><Warehouse size={16} /><span>Capacity</span><b>{topDest.available_capacity.toLocaleString()}</b></div>
                <div><Hospital size={16} /><span>Healthcare</span><b>{scoreLabel(topDest.healthcare_score)}</b></div>
                <div><Droplets size={16} /><span>Water</span><b>{scoreLabel(topDest.water_score)}</b></div>
                <div><ShieldAlert size={16} /><span>Route Safety</span><b>{scoreLabel(topDest.route_safety_score)}</b></div>
                <div><Users size={16} /><span>Allocated</span><b>{topDest.families_allocated} families</b></div>
              </div>
            </div>
          )}

          {/* Allocations */}
          <div className="plan-alloc card">
            <div className="card-head"><div><h2>Population Allocation</h2><p>{allocatedDests.length} destination(s) · {plan.total_families_allocated}/{plan.affected_families} families allocated</p></div>
              <span className="live-badge"><span /> Live Plan</span></div>
            <div className="alloc-grid">
              {allocatedDests.map(d => (
                <div key={d.destination_id} className="alloc-card safe">
                  <Warehouse size={20} />
                  <div>
                    <b>{d.destination_name}</b>
                    <span>Score: {Math.round(d.weighted_total * 100)}/100</span>
                    <strong>{d.families_allocated} families</strong>
                    <small>{d.route_distance_km} km · {d.route_status}</small>
                  </div>
                </div>
              ))}
            </div>
            <div className="plan-summary-line">
              <CheckCircle2 size={14} /> {totalEval} candidates evaluated · {plan.rejected_destinations.length} rejected
            </div>
          </div>

          {/* Rejected */}
          {plan.rejected_destinations.length > 0 && (
            <div className="plan-rejected card">
              <div className="card-head"><div><h2>Rejected Destinations</h2><p>Failed hard constraint filters</p></div></div>
              <div className="rejected-list">
                {plan.rejected_destinations.map(rd => (
                  <div key={rd.destination_id} className="rejected-item">
                    <AlertTriangle size={14} />
                    <div>
                      <b>{rd.destination_name}</b>
                      <span>{rd.rejection_reasons.join("; ")}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Summary text */}
          {plan.summary_text && (
            <div className="plan-text card">
              <div className="card-head"><div><h2>Plan Summary</h2><p>Rule-based explanation</p></div></div>
              <pre className="summary-pre">{plan.summary_text}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
