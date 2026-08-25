import React from "react";
import useVillages from "../hooks/useVillages";
import {
  ShieldAlert, AlertTriangle, CheckCircle2, CircleAlert,
  ArrowUpRight, Loader2,
} from "lucide-react";

function riskColor(risk) {
  if (risk >= 0.75) return "red";
  if (risk >= 0.55) return "orange";
  if (risk >= 0.35) return "yellow";
  return "green";
}

function riskLabel(risk) {
  if (risk >= 0.75) return "Extreme";
  if (risk >= 0.55) return "High";
  if (risk >= 0.35) return "Moderate";
  return "Low";
}

export default function RiskOverview() {
  const { villages, count, loading, error } = useVillages();

  const sorted = [...villages].sort((a, b) => b.river_flood_risk - a.river_flood_risk);

  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Risk Overview</h2><p>Live risk assessment across all monitored villages</p></div>
        <span className="page-badge">{count} villages tracked</span>
      </div>

      {loading && <div className="page-loading"><Loader2 size={24} className="spin" /><span>Loading villages…</span></div>}
      {error && <div className="error-banner error-generic"><CircleAlert size={16} /><span>{error.message}</span></div>}

      {!loading && !error && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Village</th>
                <th>District</th>
                <th>State</th>
                <th>Population</th>
                <th>Flood Risk</th>
                <th>Landslide Risk</th>
                <th>Combined</th>
                <th>Elevation</th>
                <th>River Dist.</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((v) => {
                const combined = (v.river_flood_risk * 0.6 + v.landslide_risk * 0.4);
                return (
                  <tr key={v.id}>
                    <td><b>{v.name}</b><small>{v.id}</small></td>
                    <td>{v.district}</td>
                    <td>{v.state}</td>
                    <td>{v.population.toLocaleString()}</td>
                    <td><span className={`risk-pill ${riskColor(v.river_flood_risk)}`}>{riskLabel(v.river_flood_risk)} ({(v.river_flood_risk * 100).toFixed(0)}%)</span></td>
                    <td><span className={`risk-pill ${riskColor(v.landslide_risk)}`}>{riskLabel(v.landslide_risk)} ({(v.landslide_risk * 100).toFixed(0)}%)</span></td>
                    <td><span className={`risk-pill ${riskColor(combined)}`}>{(combined * 100).toFixed(0)}%</span></td>
                    <td>{v.elevation_m}m</td>
                    <td>{v.river_distance_km} km</td>
                    <td>
                      {v.is_source_village
                        ? <span className="status-pill source"><AlertTriangle size={11} /> Source</span>
                        : v.road_status === "blocked"
                        ? <span className="status-pill blocked">Blocked</span>
                        : <span className="status-pill ok"><CheckCircle2 size={11} /> OK</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
