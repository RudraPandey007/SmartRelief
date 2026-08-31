import React, { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  LayoutDashboard, ShieldAlert, Users, MapPinned, Navigation,
  House, Bell, FileText, Settings, ChevronDown, Menu, X,
  AlertTriangle, UserRound, Warehouse, ArrowUpRight, Hospital,
  Droplets, Route, SlidersHorizontal,
  CheckCircle2, RefreshCw, CloudRain, Activity, Clock3, Loader2,
  CircleAlert, Sun, Moon,
} from "lucide-react";
import "lucide-react";
import "leaflet/dist/leaflet.css";
import "./styles.css";

import RiskMap from "./components/RiskMap";

import useRelocationPlan from "./hooks/useRelocationPlan";
import useDashboardOverview from "./hooks/useDashboardOverview";
import useSimulation from "./hooks/useSimulation";

import RiskOverview from "./pages/RiskOverview";
import AffectedPopulation from "./pages/AffectedPopulation";
import RelocationPlanner from "./pages/RelocationPlanner";
import Destinations from "./pages/Destinations";
import RoutesPage from "./pages/Routes";
import Resources from "./pages/Resources";
import Alerts from "./pages/Alerts";
import Reports from "./pages/Reports";
import SettingsPage from "./pages/Settings";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const NAV = [
  ["Dashboard", LayoutDashboard],
  ["Risk Overview", ShieldAlert],
  ["Affected Population", Users],
  ["Relocation Planner", MapPinned],
  ["Destinations", House],
  ["Routes", Navigation],
  ["Resources", Warehouse],
  ["Alerts & Notifications", Bell],
  ["Reports", FileText],
  ["Settings", Settings],
];

/* ------------------------------------------------------------------ */
/*  Dark Theme Hook                                                    */
/* ------------------------------------------------------------------ */

function useDarkTheme() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem("theme-dark");
    if (stored !== null) return stored === "true";
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.setAttribute("data-theme", "dark");
    } else {
      root.removeAttribute("data-theme");
    }
    localStorage.setItem("theme-dark", String(dark));
  }, [dark]);

  return [dark, setDark];
}

/* ------------------------------------------------------------------ */
/*  Notification Bell Hook                                             */
/* ------------------------------------------------------------------ */

function useNotifications(plan) {
  const [readIds, setReadIds] = useState(() => {
    try { return JSON.parse(localStorage.getItem("notif-read") || "[]"); } catch { return []; }
  });

  const notifications = useMemo(() => {
    if (!plan) return [];
    const list = [];

    // Villages at critical or high risk
    (plan.ranked_destinations || []).forEach((d) => {
      if (d.risk_classification === "critical" || d.risk_classification === "high") {
        list.push({
          id: `risk-${d.destination_id}`,
          text: `\u26A0\uFE0F ${d.destination_name} has crossed into ${d.risk_classification} risk`,
        });
      }
    });

    // Rejected destinations due to blocked/unavailable routes
    (plan.rejected_destinations || []).forEach((rd) => {
      const reasons = rd.rejection_reasons || [];
      const hasRouteIssue = reasons.some(
        (r) => /blocked|unavailable|route/i.test(r)
      );
      if (hasRouteIssue) {
        list.push({
          id: `route-${rd.destination_id}`,
          text: `\uD83D\uDEA7 Route to ${rd.destination_name} is currently blocked`,
        });
      }
    });

    // Most recent plan generation
    if (plan.total_families_allocated > 0) {
      list.push({
        id: `plan-${plan.village_name}`,
        text: `\u2705 Relocation plan generated for ${plan.village_name} \u2014 ${plan.total_families_allocated} families allocated`,
      });
    }

    return list;
  }, [plan]);

  const markRead = useCallback((id) => {
    setReadIds((prev) => {
      const next = [...prev, id];
      localStorage.setItem("notif-read", JSON.stringify(next));
      return next;
    });
  }, []);

  const unreadCount = notifications.filter((n) => !readIds.includes(n.id)).length;

  return { notifications, readIds, markRead, unreadCount };
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Map a 0-1 float score to a human label. */
function scoreLabel(score) {
  if (score == null) return "N/A";
  if (score >= 0.8) return "Good";
  if (score >= 0.5) return "Moderate";
  return "Limited";
}

/** Map combined_risk (0-1) to a display string. */
function riskDisplay(risk) {
  if (risk == null) return "N/A";
  if (risk >= 0.75) return "Extreme";
  if (risk >= 0.55) return "High";
  if (risk >= 0.35) return "Moderate";
  return "Low";
}

/** Map risk_classification string to a tone key for CSS. */
function riskTone(cls) {
  if (cls === "extreme") return "red";
  if (cls === "high") return "orange";
  if (cls === "medium") return "yellow";
  return "low";
}

/** Format number with commas. */
function fmt(n) {
  if (n == null) return "\u2014";
  return n.toLocaleString();
}

/* ------------------------------------------------------------------ */
/*  Metric card                                                        */
/* ------------------------------------------------------------------ */

function Metric({ icon: Icon, label, value, note, tone }) {
  return (
    <article className={`metric ${tone}`}>
      <div>
        <span className="metric-label">{label}</span>
        <strong>{value}</strong>
        <small>{note}</small>
      </div>
      <div className="metric-icon"><Icon size={21} /></div>
    </article>
  );
}

/* ------------------------------------------------------------------ */
/*  Error banner                                                       */
/* ------------------------------------------------------------------ */

function ErrorBanner({ error, onRetry }) {
  if (!error) return null;

  const isAuth = error.code === "AUTH_MISMATCH";
  const isRate = error.code === "RATE_LIMITED";

  return (
    <div className={`error-banner ${isAuth ? "error-auth" : isRate ? "error-rate" : "error-generic"}`}>
      <CircleAlert size={16} />
      <span>{error.message}</span>
      {onRetry && <button onClick={onRetry} className="retry-btn">Retry</button>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Loading spinner                                                    */
/* ------------------------------------------------------------------ */

function Spinner({ size = 20, label }) {
  return (
    <span className="spinner-inline">
      <Loader2 size={size} className="spin" />
      {label && <small>{label}</small>}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Notification Dropdown                                              */
/* ------------------------------------------------------------------ */

function NotificationDropdown({ notifications, readIds, markRead, unreadCount }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Close on outside click
  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div className="notif-wrap" ref={ref}>
      <button
        className={`icon-btn bell${unreadCount > 0 ? " has-unread" : ""}`}
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && <i>{unreadCount}</i>}
      </button>
      {open && (
        <div className="notif-dropdown">
          <div className="notif-header">
            <strong>Notifications</strong>
            {unreadCount > 0 && <small>{unreadCount} unread</small>}
          </div>
          <div className="notif-list">
            {notifications.length === 0 && (
              <div className="notif-empty">
                <CheckCircle2 size={18} />
                <span>No alerts right now</span>
              </div>
            )}
            {notifications.map((n) => (
              <div
                key={n.id}
                className={`notif-item${readIds.includes(n.id) ? " read" : ""}`}
                onClick={() => markRead(n.id)}
              >
                <span>{n.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Dashboard                                                          */
/* ------------------------------------------------------------------ */

function Dashboard() {
  /* ---- hooks ---- */
  const { plan, loading: planLoading, error: planError, refetch: refetchPlan } = useRelocationPlan("V001");
  const { overview, loading: ovLoading, error: ovError, refetch: refetchOv } = useDashboardOverview();
  const {
    simulated, sliders, setSlider,
    runSimulation, resetSimulation,
    simResult, simLoading, simError,
  } = useSimulation("V001");

  /* Use the "after" plan when simulating, otherwise the base plan */
  const activePlan = simulated && simResult?.after ? simResult.after : plan;
  const basePlan = plan;

  /* Top destination */
  const topDest = activePlan?.ranked_destinations?.[0] || null;
  const allocatedDests = (activePlan?.ranked_destinations || []).filter((d) => d.families_allocated > 0);
  const totalEvaluated = (activePlan?.ranked_destinations?.length || 0) + (activePlan?.rejected_destinations?.length || 0);
  const totalRejected = activePlan?.rejected_destinations?.length || 0;

  /* ---- loading / error states ---- */
  const isLoading = planLoading || ovLoading;
  const mainError = planError || ovError;

  /* ---- simulation change summary ---- */
  const simChanges = useMemo(() => {
    if (!simResult?.changes_summary) return null;
    return simResult.changes_summary;
  }, [simResult]);

  /* ---- modal state for expanded views ---- */
  const [showFullRec, setShowFullRec] = useState(false);
  const [showAllRejected, setShowAllRejected] = useState(false);

  return (
    <>
      {/* Global error banner */}
      <ErrorBanner error={mainError} onRetry={() => { refetchPlan(); refetchOv(); }} />

      {/* ---- Top metrics ---- */}
      <div className="metrics">
        <Metric
          icon={ShieldAlert}
          label="High Risk Villages"
          value={ovLoading ? "\u2026" : fmt(
            (overview?.villages_by_risk?.extreme || 0) + (overview?.villages_by_risk?.high || 0)
          )}
          note={overview
            ? `${overview.villages_by_risk?.extreme || 0} extreme \u00B7 ${overview.villages_by_risk?.high || 0} high`
            : "Loading\u2026"}
          tone="red"
        />
        <Metric
          icon={Users}
          label="Affected Families"
          value={planLoading ? "\u2026" : fmt(activePlan?.affected_families)}
          note={activePlan
            ? `${fmt(activePlan.population)} total population \u00B7 ${activePlan.state}`
            : "Loading\u2026"}
          tone="orange"
        />
        <Metric
          icon={UserRound}
          label="Total Population"
          value={ovLoading ? "\u2026" : fmt(overview?.total_population)}
          note={overview ? `Across ${overview.total_villages} villages` : "Loading\u2026"}
          tone="purple"
        />
        <Metric
          icon={Warehouse}
          label="Available Shelters"
          value={ovLoading ? "\u2026" : fmt(overview?.available_shelter_capacity)}
          note={overview
            ? `${overview.total_shelters} shelters \u00B7 ${fmt(overview.total_shelter_capacity)} total beds`
            : "Loading\u2026"}
          tone="green"
        />
      </div>

      {/* ---- Map + Recommendation ---- */}
      <div className="grid-main">
        <section className="card map-card">
          <div className="card-head">
            <div>
              <h2>Risk Map Overview</h2>
              <p>
                {activePlan
                  ? `Source: ${activePlan.village_name}, ${activePlan.district} \u2014 ${activePlan.ranked_destinations?.length || 0} destinations evaluated`
                  : "Live hazard zones, affected settlements and relocation route"}
              </p>
            </div>
            <button className="filter-btn"><SlidersHorizontal size={15} /> Layers</button>
          </div>
          <RiskMap plan={activePlan} />
        </section>

        <section className="card recommendation">
          <div className="card-head">
            <div><h2>Top Relocation Recommendation</h2><p>Optimized using safety, capacity, routes &amp; resources</p></div>
            {topDest && <span className="status good"><CheckCircle2 size={13} /> Recommended</span>}
          </div>

          {planLoading ? (
            <div className="rec-loading"><Spinner size={28} label="Generating plan…" /></div>
          ) : topDest ? (
            <>
              <div className="rec-hero">
                <div><span>Best Destination</span><h3>{topDest.destination_name}</h3></div>
                <div className="score">
                  <b>{Math.round(topDest.weighted_total * 100)}</b>
                  <span>/100</span>
                </div>
              </div>
              <div className="rec-list">
                <div><Route /><span>Distance</span><b>{topDest.route_distance_km} km</b></div>
                <div><Users /><span>Available Capacity</span><b>{fmt(topDest.available_capacity)} families</b></div>
                <div><Hospital /><span>Healthcare Access</span><b>{scoreLabel(topDest.healthcare_score)}</b></div>
                <div><Droplets /><span>Water Availability</span><b>{scoreLabel(topDest.water_score)}</b></div>
                <div><ShieldAlert /><span>Route Safety</span>
                  <b className={topDest.route_safety_score >= 0.7 ? "text-green" : topDest.route_safety_score >= 0.4 ? "text-orange" : "text-red"}>
                    {scoreLabel(topDest.route_safety_score)}
                  </b>
                </div>
              </div>
              <button className="primary-btn" onClick={() => setShowFullRec(true)}>View Full Recommendation <ArrowUpRight size={16} /></button>
            </>
          ) : (
            <div className="rec-empty">No destinations available for this village.</div>
          )}
        </section>
      </div>

      {/* ---- Hazard, Population, Alerts ---- */}
      <div className="grid-three">
        <section className="card">
          <div className="card-head"><div><h2>Hazard Summary</h2><p>Current conditions</p></div><Activity size={19} /></div>
          <div className="hazard-list">
            <div><CloudRain /><span>Flood Risk</span>
              <b className={activePlan?.hazard_score >= 0.7 ? "text-red" : activePlan?.hazard_score >= 0.4 ? "text-orange" : ""}>
                {activePlan ? scoreLabel(activePlan.hazard_score) : "\u2026"}
              </b>
            </div>
            <div><ShieldAlert /><span>Combined Risk</span>
              <b className={activePlan?.combined_risk >= 0.55 ? "text-red" : activePlan?.combined_risk >= 0.35 ? "text-orange" : ""}>
                {activePlan ? riskDisplay(activePlan.combined_risk) : "\u2026"}
              </b>
            </div>
            <div><Activity /><span>Risk Classification</span>
              <b className={`text-${riskTone(activePlan?.risk_classification)}`}>
                {activePlan ? activePlan.risk_classification?.toUpperCase() : "\u2026"}
              </b>
            </div>
            <div><AlertTriangle /><span>Vulnerability Score</span>
              <b>{activePlan ? `${Math.round(activePlan.vulnerability_score * 100)}%` : "\u2026"}</b>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-head"><div><h2>Affected Population</h2><p>Family vulnerability breakdown</p></div><Users size={19} /></div>
          <div className="donut-row">
            <div className="donut">
              <div>
                <b>{activePlan ? fmt(activePlan.affected_families) : "\u2026"}</b>
                <span>Families</span>
              </div>
            </div>
            <div className="breakdown">
              <span><i className="dot children" />Households <b>{activePlan ? fmt(activePlan.households) : "\u2026"}</b></span>
              <span><i className="dot adults" />Total Population <b>{activePlan ? fmt(activePlan.population) : "\u2026"}</b></span>
              <span><i className="dot elderly" />Families Allocated <b>{activePlan ? fmt(activePlan.total_families_allocated) : "\u2026"}</b></span>
              <span><i className="dot others" />Unallocated <b>{activePlan ? fmt(activePlan.unallocated_families) : "\u2026"}</b></span>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-head"><div><h2>Rejected Destinations</h2><p>Hard constraint failures</p></div><button className="link-btn" onClick={() => setShowAllRejected(true)}>View all</button></div>
          <div className="alerts">
            {(activePlan?.rejected_destinations || []).slice(0, 5).map((rd, i) => (
              <div key={rd.destination_id || i}>
                <AlertTriangle className="alert-red" />
                <span>
                  <b>{rd.destination_name}</b>
                  <small>{rd.rejection_reasons?.[0] || "Rejected by safety constraints"}</small>
                </span>
              </div>
            ))}
            {(!activePlan?.rejected_destinations || activePlan.rejected_destinations.length === 0) && (
              <div><CheckCircle2 className="alert-green" /><span><b>No rejections</b><small>All candidates passed filters</small></span></div>
            )}
          </div>
        </section>
      </div>

      {/* ---- Relocation Plan Summary ---- */}
      <section className="card relocation">
        <div className="card-head">
          <div>
            <h2>Relocation Plan Summary</h2>
            <p>Explainable population allocation generated by the decision engine</p>
          </div>
          {activePlan && <span className="live"><span /> Live Plan</span>}
        </div>

        {planLoading ? (
          <div className="rec-loading"><Spinner size={28} label="Building allocation…" /></div>
        ) : activePlan ? (
          <>
            <div className="allocation">
              {/* Source box */}
              <div className="allocation-box danger">
                <AlertTriangle />
                <div>
                  <b>{activePlan.village_name}</b>
                  <span>{activePlan.risk_classification?.toUpperCase()} Risk</span>
                  <strong>{fmt(activePlan.affected_families)} Families</strong>
                </div>
              </div>

              <div className="arrow">→</div>

              {/* Dynamic allocation boxes */}
              {allocatedDests.map((d, i) => (
                <React.Fragment key={d.destination_id}>
                  {i > 0 && <div className="plus">+</div>}
                  <div className="allocation-box safe">
                    <Warehouse />
                    <div>
                      <b>{d.destination_name}</b>
                      <span>{Math.round(d.weighted_total * 100)}/100 Score</span>
                      <strong>{fmt(d.families_allocated)} Families</strong>
                    </div>
                  </div>
                </React.Fragment>
              ))}

              {allocatedDests.length === 0 && (
                <div className="allocation-box">
                  <CircleAlert />
                  <div>
                    <b>No destinations found</b>
                    <span>All candidates rejected</span>
                    <strong>0 Families allocated</strong>
                  </div>
                </div>
              )}

              <div className="equals">=</div>

              <div className="total">
                <CheckCircle2 />
                <b>Total Relocated</b>
                <strong>{fmt(activePlan.total_families_allocated)} Families</strong>
              </div>
            </div>

            <div className="plan-bottom">
              <span>
                <CheckCircle2 size={15} />
                {totalEvaluated} candidates evaluated · {totalRejected} rejected by hard safety constraints
              </span>
              <button className="link-btn">View Detailed Plan <ArrowUpRight size={14} /></button>
            </div>
          </>
        ) : null}
      </section>

      {/* ---- Simulation ---- */}
      <section className="card simulation">
        <div>
          <h2>What-If Simulation</h2>
          <p>Test how the recommendation changes when conditions evolve.</p>
          {simChanges && (
            <div className="sim-changes">
              {Object.entries(simChanges).map(([k, v]) => (
                <span key={k}><b>{k}:</b> {typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
              ))}
            </div>
          )}
        </div>
        <div className="sliders">
          <label>
            Rainfall Multiplier <b>{(0.1 + (sliders.rainfall_mm / 100) * 9.9).toFixed(1)}×</b>
            <input
              type="range"
              min="1" max="100" step="1"
              value={sliders.rainfall_mm}
              onChange={(e) => setSlider("rainfall_mm", e.target.value)}
            />
          </label>
          <label>
            Shelter Occupancy <b>{sliders.occupancy_pct}%</b>
            <input
              type="range"
              min="0" max="100" step="1"
              value={sliders.occupancy_pct}
              onChange={(e) => setSlider("occupancy_pct", e.target.value)}
            />
          </label>
          <label>
            Road Accessibility <b>{sliders.road_access_pct}%</b>
            <input
              type="range"
              min="0" max="100" step="1"
              value={sliders.road_access_pct}
              onChange={(e) => setSlider("road_access_pct", e.target.value)}
            />
          </label>
        </div>
        <button
          className="primary-btn simulation-btn"
          onClick={simulated ? resetSimulation : runSimulation}
          disabled={simLoading}
        >
          {simLoading ? (
            <><Loader2 size={16} className="spin" /> Running…</>
          ) : simulated ? (
            <><RefreshCw size={16} /> Reset Scenario</>
          ) : (
            <><RefreshCw size={16} /> Run Simulation</>
          )}
        </button>
        {simError && (
          <div className="sim-error">
            <CircleAlert size={14} /> {simError.message}
          </div>
        )}
      </section>

      {/* ---- Full Recommendation Modal ---- */}
      {showFullRec && topDest && (
        <div className="modal-overlay" onClick={() => setShowFullRec(false)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h2>Full Recommendation Detail</h2>
              <button className="modal-close" onClick={() => setShowFullRec(false)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="rec-hero" style={{ marginBottom: 16 }}>
                <div><span>Best Destination</span><h3>{topDest.destination_name}</h3></div>
                <div className="score">
                  <b>{Math.round(topDest.weighted_total * 100)}</b>
                  <span>/100</span>
                </div>
              </div>

              <h3 style={{ fontSize: 12, margin: '0 0 8px' }}>Destination Scores</h3>
              <div className="dest-details">
                <div><span>Safety Score</span><b>{scoreLabel(topDest.safety_score)}</b></div>
                <div><span>Capacity Score</span><b>{scoreLabel(topDest.capacity_score)}</b></div>
                <div><span>Route Safety</span><b>{scoreLabel(topDest.route_safety_score)}</b></div>
                <div><span>Healthcare Access</span><b>{scoreLabel(topDest.healthcare_score)}</b></div>
                <div><span>Water Availability</span><b>{scoreLabel(topDest.water_score)}</b></div>
                <div><span>Vulnerability Fit</span><b>{scoreLabel(topDest.vulnerability_fit_score)}</b></div>
                <div><span>Distance Score</span><b>{scoreLabel(topDest.distance_score)}</b></div>
                <div><span>Weighted Total</span><b>{topDest.weighted_total?.toFixed(4)}</b></div>
              </div>

              <h3 style={{ fontSize: 12, margin: '16px 0 8px' }}>Capacity & Allocation</h3>
              <div className="dest-details">
                <div><span>Total Capacity</span><b>{fmt(topDest.total_capacity)}</b></div>
                <div><span>Available Capacity</span><b>{fmt(topDest.available_capacity)}</b></div>
                <div><span>Families Allocated</span><b>{fmt(topDest.families_allocated)}</b></div>
              </div>
              {topDest.allocation_breakdown && (
                <div style={{ marginTop: 8 }}>
                  <small style={{ fontSize: 9, color: 'var(--muted)' }}>Allocation Breakdown:</small>
                  <div className="dest-details" style={{ marginTop: 4 }}>
                    <div><span>Elderly/Special Needs</span><b>{topDest.allocation_breakdown.priority_elderly_special_needs || 0}</b></div>
                    <div><span>Children</span><b>{topDest.allocation_breakdown.priority_children || 0}</b></div>
                    <div><span>General Population</span><b>{topDest.allocation_breakdown.general_population || 0}</b></div>
                  </div>
                </div>
              )}

              <h3 style={{ fontSize: 12, margin: '16px 0 8px' }}>Route Details</h3>
              <div className="dest-details">
                <div><span>Route Distance</span><b>{topDest.route_distance_km} km</b></div>
                <div><span>Route Time</span><b>{topDest.route_time_min} min</b></div>
                <div><span>Route Status</span><b>{topDest.route_status}</b></div>
                <div><span>Flooded</span><b>{topDest.is_flooded ? 'Yes' : 'No'}</b></div>
                <div><span>Landslide Affected</span><b>{topDest.is_landslide_affected ? 'Yes' : 'No'}</b></div>
                <div><span>Rank</span><b>#{topDest.rank}</b></div>
              </div>

              {topDest.allocation_reasons && topDest.allocation_reasons.length > 0 && (
                <>
                  <h3 style={{ fontSize: 12, margin: '16px 0 8px' }}>Allocation Reasons</h3>
                  <div className="rejected-list">
                    {topDest.allocation_reasons.map((reason, i) => (
                      <div key={i} style={{ background: 'var(--safe-bg)', borderColor: 'var(--safe-border)' }}>
                        <CheckCircle2 style={{ color: 'var(--green)' }} />
                        <span style={{ fontSize: 9, color: 'var(--safe-text)' }}>{reason}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ---- All Rejected Destinations Modal ---- */}
      {showAllRejected && (
        <div className="modal-overlay" onClick={() => setShowAllRejected(false)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <h2>All Rejected Destinations</h2>
                <p style={{ fontSize: 9, color: 'var(--muted)', margin: '4px 0 0' }}>
                  {totalRejected} candidate(s) rejected by hard safety constraints
                </p>
              </div>
              <button className="modal-close" onClick={() => setShowAllRejected(false)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="rejected-list">
                {(activePlan?.rejected_destinations || []).map((rd, i) => (
                  <div key={rd.destination_id || i}>
                    <AlertTriangle />
                    <div>
                      <b>{rd.destination_name}</b>
                      {rd.rejection_reasons && rd.rejection_reasons.length > 0 ? (
                        rd.rejection_reasons.map((r, j) => (
                          <span key={j} style={{ display: 'block', marginTop: j > 0 ? 4 : 0 }}>{r}</span>
                        ))
                      ) : (
                        <span>Rejected by safety constraints</span>
                      )}
                    </div>
                  </div>
                ))}
                {totalRejected === 0 && (
                  <div style={{ background: 'var(--safe-bg)', borderColor: 'var(--safe-border)' }}>
                    <CheckCircle2 style={{ color: 'var(--green)' }} />
                    <div><b>No rejections</b><span>All candidates passed filters</span></div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Page router                                                        */
/* ------------------------------------------------------------------ */

const PAGES = {
  "Dashboard": Dashboard,
  "Risk Overview": RiskOverview,
  "Affected Population": AffectedPopulation,
  "Relocation Planner": RelocationPlanner,
  "Destinations": Destinations,
  "Routes": RoutesPage,
  "Resources": Resources,
  "Alerts & Notifications": Alerts,
  "Reports": Reports,
  "Settings": SettingsPage,
};

/* ------------------------------------------------------------------ */
/*  App                                                                */
/* ------------------------------------------------------------------ */

function App() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [active, setActive] = useState("Dashboard");
  const [dark, setDark] = useDarkTheme();

  /* Notifications — pass plan from top-level so bell has data on every page */
  const { plan } = useRelocationPlan("V001");
  const { notifications, readIds, markRead, unreadCount } = useNotifications(plan);

  return (
    <div className="app">
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><ShieldAlert size={23} /></div>
          <div><strong>SMART RELIEF</strong><small>Disaster Decision Support</small></div>
          <button className="close-mobile" onClick={() => setMobileOpen(false)}><X size={20} /></button>
        </div>
        <nav>
          {NAV.map(([label, Icon]) => (
            <button key={label} className={active === label ? "active" : ""} onClick={() => { setActive(label); setMobileOpen(false); }}>
              <Icon size={17} /><span>{label}</span>
              {label === "Alerts & Notifications" && <em>3</em>}
              {label === "Risk Overview" && <ChevronDown size={13} className="nav-arrow" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">Smart Relief v1.0 • SIH Prototype</div>
      </aside>

      <main className="main">
        <header className="topbar">
          <button className="hamburger" onClick={() => setMobileOpen(true)}><Menu /></button>
          <div className="heading">
            <h1>{active}</h1>
            <p>Real-time overview of hazards, affected areas and relocation recommendations</p>
          </div>
          <div className="top-actions">
            <NotificationDropdown
              notifications={notifications}
              readIds={readIds}
              markRead={markRead}
              unreadCount={unreadCount}
            />
            <button
              className="icon-btn theme-toggle"
              onClick={() => setDark((d) => !d)}
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
              title={dark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        <section className="content">
          {(() => { const Page = PAGES[active]; return Page ? <Page /> : <Dashboard />; })()}
        </section>
      </main>

      <div className="mobile-bottom">
        <button className={active === "Dashboard" ? "active" : ""} onClick={() => setActive("Dashboard")}><LayoutDashboard /><span>Dashboard</span></button>
        <button onClick={() => setActive("Relocation Planner")}><MapPinned /><span>Relocation</span></button>
        <button onClick={() => setActive("Routes")}><Navigation /><span>Routes</span></button>
        <button onClick={() => setActive("Alerts & Notifications")}><Bell /><span>Alerts</span></button>
        <button onClick={() => setMobileOpen(true)}><Menu /><span>More</span></button>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
