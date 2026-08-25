import React, { useMemo } from "react";
import useVillages from "../hooks/useVillages";
import useDashboardOverview from "../hooks/useDashboardOverview";
import {
  AlertTriangle, CloudRain, ShieldAlert, Bell, CheckCircle2,
  Clock3, Loader2, CircleAlert, Navigation,
} from "lucide-react";

function now() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Alerts() {
  const { villages, loading: vLoading } = useVillages();
  const { overview, loading: oLoading } = useDashboardOverview();

  const alerts = useMemo(() => {
    if (!villages.length) return [];
    const list = [];

    // High-risk villages
    const highRisk = villages.filter(v => v.river_flood_risk >= 0.75);
    if (highRisk.length > 0) {
      list.push({
        type: "critical",
        icon: AlertTriangle,
        title: `Extreme Flood Risk — ${highRisk.length} villages`,
        detail: highRisk.map(v => v.name).join(", "),
        time: now(),
      });
    }

    // Blocked routes
    if (overview?.blocked_routes > 0) {
      list.push({
        type: "critical",
        icon: Navigation,
        title: `${overview.blocked_routes} Route(s) Blocked`,
        detail: "Bridge collapses or road damage — alternate routes required",
        time: now(),
      });
    }

    // Degraded routes
    if (overview?.degraded_routes > 0) {
      list.push({
        type: "warning",
        icon: Navigation,
        title: `${overview.degraded_routes} Route(s) Degraded`,
        detail: "Partial flooding or landslides — reduced accessibility",
        time: now(),
      });
    }

    // Source villages
    const sources = villages.filter(v => v.is_source_village);
    sources.forEach(v => {
      list.push({
        type: "critical",
        icon: ShieldAlert,
        title: `Evacuation Required — ${v.name}`,
        detail: `Risk: ${(v.river_flood_risk * 100).toFixed(0)}% · Population: ${v.population.toLocaleString()}`,
        time: now(),
      });
    });

    // High landslide risk
    const landslide = villages.filter(v => v.landslide_risk >= 0.6);
    if (landslide.length > 0) {
      list.push({
        type: "warning",
        icon: CloudRain,
        title: `Landslide Alert — ${landslide.length} village(s)`,
        detail: landslide.map(v => `${v.name} (${(v.landslide_risk * 100).toFixed(0)}%)`).join(", "),
        time: now(),
      });
    }

    // Villages without healthcare
    const noHealth = villages.filter(v => !v.has_healthcare);
    if (noHealth.length > 0) {
      list.push({
        type: "info",
        icon: CircleAlert,
        title: `${noHealth.length} Village(s) Without Healthcare`,
        detail: noHealth.map(v => v.name).join(", "),
        time: now(),
      });
    }

    // Shelter capacity
    if (overview && overview.available_shelter_capacity < overview.total_shelter_capacity * 0.3) {
      list.push({
        type: "warning",
        icon: AlertTriangle,
        title: "Shelter Capacity Running Low",
        detail: `${overview.available_shelter_capacity}/${overview.total_shelter_capacity} beds available`,
        time: now(),
      });
    }

    // All clear
    if (list.length === 0) {
      list.push({
        type: "ok",
        icon: CheckCircle2,
        title: "All Clear",
        detail: "No active alerts — all systems nominal",
        time: now(),
      });
    }

    return list;
  }, [villages, overview]);

  const loading = vLoading || oLoading;

  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Alerts &amp; Notifications</h2><p>Real-time system alerts based on hazard monitoring</p></div>
        <span className="page-badge">{alerts.filter(a => a.type === "critical").length} critical</span>
      </div>

      {loading && <div className="page-loading"><Loader2 size={24} className="spin" /><span>Loading alerts…</span></div>}

      {!loading && (
        <div className="alerts-list">
          {alerts.map((a, i) => {
            const Icon = a.icon;
            return (
              <div key={i} className={`alert-row alert-${a.type}`}>
                <div className="alert-icon"><Icon size={18} /></div>
                <div className="alert-body">
                  <b>{a.title}</b>
                  <span>{a.detail}</span>
                </div>
                <time><Clock3 size={12} /> {a.time}</time>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
