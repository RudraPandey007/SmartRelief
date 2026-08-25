import React, { useMemo } from "react";
import useVillages from "../hooks/useVillages";
import useDashboardOverview from "../hooks/useDashboardOverview";
import {
  FileText, Loader2, CircleAlert, BarChart3, PieChart,
  ShieldAlert, Users, Warehouse, Navigation,
} from "lucide-react";

export default function Reports() {
  const { villages, loading: vLoading } = useVillages();
  const { overview, loading: oLoading } = useDashboardOverview();

  const stats = useMemo(() => {
    if (!villages.length || !overview) return null;

    const states = {};
    villages.forEach(v => {
      states[v.state] = (states[v.state] || 0) + 1;
    });

    const roadStatus = { available: 0, degraded: 0, blocked: 0 };
    villages.forEach(v => { roadStatus[v.road_status] = (roadStatus[v.road_status] || 0) + 1; });

    const riskDist = { extreme: 0, high: 0, medium: 0, low: 0 };
    villages.forEach(v => {
      const r = v.river_flood_risk;
      if (r >= 0.75) riskDist.extreme++;
      else if (r >= 0.55) riskDist.high++;
      else if (r >= 0.35) riskDist.medium++;
      else riskDist.low++;
    });

    const avgFlood = villages.reduce((s, v) => s + v.river_flood_risk, 0) / villages.length;
    const avgLandslide = villages.reduce((s, v) => s + v.landslide_risk, 0) / villages.length;
    const avgElevation = villages.reduce((s, v) => s + v.elevation_m, 0) / villages.length;

    return { states, roadStatus, riskDist, avgFlood, avgLandslide, avgElevation };
  }, [villages, overview]);

  const loading = vLoading || oLoading;

  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Reports</h2><p>Aggregate analytics and system performance metrics</p></div>
      </div>

      {loading && <div className="page-loading"><Loader2 size={24} className="spin" /><span>Loading reports…</span></div>}


      {stats && (
        <>
          {/* Overview stats */}
          <div className="stat-cards">
            <div className="stat-card">
              <div className="stat-icon red"><ShieldAlert size={20} /></div>
              <div><span>Total Villages</span><strong>{overview.total_villages}</strong></div>
            </div>
            <div className="stat-card">
              <div className="stat-icon orange"><Users size={20} /></div>
              <div><span>Total Population</span><strong>{overview.total_population.toLocaleString()}</strong></div>
            </div>
            <div className="stat-card">
              <div className="stat-icon green"><Warehouse size={20} /></div>
              <div><span>Shelter Capacity</span><strong>{overview.available_shelter_capacity.toLocaleString()}</strong><small>of {overview.total_shelter_capacity.toLocaleString()} total</small></div>
            </div>
            <div className="stat-card">
              <div className="stat-icon purple"><Navigation size={20} /></div>
              <div><span>Active Routes</span><strong>{overview.total_routes - overview.blocked_routes}</strong><small>{overview.blocked_routes} blocked</small></div>
            </div>
          </div>

          {/* Risk distribution */}
          <div className="report-grid">
            <div className="card">
              <div className="card-head"><div><h2>Risk Distribution</h2><p>Villages by hazard classification</p></div><PieChart size={18} /></div>
              <div className="bar-chart">
                {[
                  { label: "Extreme", count: stats.riskDist.extreme, color: "#e84f55" },
                  { label: "High", count: stats.riskDist.high, color: "#f39a2f" },
                  { label: "Medium", count: stats.riskDist.medium, color: "#f5bd48" },
                  { label: "Low", count: stats.riskDist.low, color: "#20a86b" },
                ].map(b => (
                  <div key={b.label} className="bar-row">
                    <span className="bar-label">{b.label}</span>
                    <div className="bar-track"><div className="bar-fill" style={{ width: `${(b.count / overview.total_villages) * 100}%`, background: b.color }} /></div>
                    <span className="bar-count">{b.count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-head"><div><h2>Road Status</h2><p>Infrastructure accessibility</p></div><BarChart3 size={18} /></div>
              <div className="bar-chart">
                {[
                  { label: "Available", count: stats.roadStatus.available || 0, color: "#20a86b" },
                  { label: "Degraded", count: stats.roadStatus.degraded || 0, color: "#f39a2f" },
                  { label: "Blocked", count: stats.roadStatus.blocked || 0, color: "#e84f55" },
                ].map(b => (
                  <div key={b.label} className="bar-row">
                    <span className="bar-label">{b.label}</span>
                    <div className="bar-track"><div className="bar-fill" style={{ width: `${(b.count / overview.total_villages) * 100}%`, background: b.color }} /></div>
                    <span className="bar-count">{b.count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-head"><div><h2>Averages</h2><p>Across all monitored villages</p></div></div>
              <div className="stat-list">
                <div><span>Avg Flood Risk</span><b>{(stats.avgFlood * 100).toFixed(1)}%</b></div>
                <div><span>Avg Landslide Risk</span><b>{(stats.avgLandslide * 100).toFixed(1)}%</b></div>
                <div><span>Avg Elevation</span><b>{stats.avgElevation.toFixed(0)}m</b></div>
                <div><span>Affected Population</span><b>{overview.total_affected_population.toLocaleString()}</b></div>
                <div><span>Active Plans</span><b>{overview.active_plans}</b></div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
