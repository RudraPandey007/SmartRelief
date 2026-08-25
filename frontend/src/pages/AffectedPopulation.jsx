import React from "react";
import useVillages from "../hooks/useVillages";
import { Users, Loader2, CircleAlert, UserRound, Baby, HeartPulse, Accessibility } from "lucide-react";

function riskColor(risk) {
  if (risk >= 0.75) return "red";
  if (risk >= 0.55) return "orange";
  if (risk >= 0.35) return "yellow";
  return "green";
}

export default function AffectedPopulation() {
  const { villages, count, loading, error } = useVillages();

  // Compute totals
  const totalPop = villages.reduce((s, v) => s + v.population, 0);
  const totalChildren = villages.reduce((s, v) => s + v.children_under_5, 0);
  const totalElderly = villages.reduce((s, v) => s + v.elderly_above_65, 0);
  const totalSpecial = villages.reduce((s, v) => s + v.special_assistance, 0);
  const totalHH = villages.reduce((s, v) => s + v.households, 0);

  const sorted = [...villages].sort((a, b) => b.river_flood_risk - a.river_flood_risk);

  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Affected Population</h2><p>Demographic breakdown and vulnerability analysis across villages</p></div>
      </div>

      {/* Summary cards */}
      <div className="stat-cards">
        <div className="stat-card">
          <div className="stat-icon red"><Users size={20} /></div>
          <div><span>Total Population</span><strong>{totalPop.toLocaleString()}</strong></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon orange"><Users size={20} /></div>
          <div><span>Total Households</span><strong>{totalHH.toLocaleString()}</strong></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple"><Baby size={20} /></div>
          <div><span>Children Under 5</span><strong>{totalChildren.toLocaleString()}</strong><small>{((totalChildren / totalPop) * 100).toFixed(1)}% of population</small></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon orange"><HeartPulse size={20} /></div>
          <div><span>Elderly (65+)</span><strong>{totalElderly.toLocaleString()}</strong><small>{((totalElderly / totalPop) * 100).toFixed(1)}% of population</small></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><Accessibility size={20} /></div>
          <div><span>Special Assistance</span><strong>{totalSpecial.toLocaleString()}</strong><small>{((totalSpecial / totalPop) * 100).toFixed(1)}% of population</small></div>
        </div>
      </div>

      {loading && <div className="page-loading"><Loader2 size={24} className="spin" /><span>Loading…</span></div>}
      {error && <div className="error-banner error-generic"><CircleAlert size={16} /><span>{error.message}</span></div>}

      {!loading && !error && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Village</th>
                <th>Population</th>
                <th>Households</th>
                <th>Children (&lt;5)</th>
                <th>Elderly (65+)</th>
                <th>Special Needs</th>
                <th>Vuln. Ratio</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((v) => {
                const vulnRatio = ((v.children_under_5 + v.elderly_above_65 + v.special_assistance) / v.population * 100).toFixed(1);
                return (
                  <tr key={v.id}>
                    <td><b>{v.name}</b><small>{v.id}</small></td>
                    <td>{v.population.toLocaleString()}</td>
                    <td>{v.households.toLocaleString()}</td>
                    <td>{v.children_under_5.toLocaleString()}</td>
                    <td>{v.elderly_above_65.toLocaleString()}</td>
                    <td>{v.special_assistance.toLocaleString()}</td>
                    <td><b>{vulnRatio}%</b></td>
                    <td><span className={`risk-pill ${riskColor(v.river_flood_risk)}`}>{(v.river_flood_risk * 100).toFixed(0)}%</span></td>
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
