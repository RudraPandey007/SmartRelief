import React from "react";
import { Settings as SettingsIcon, Shield, Gauge, Globe, Database } from "lucide-react";

export default function Settings() {
  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Settings</h2><p>System configuration and API status</p></div>
      </div>

      <div className="settings-grid">
        <div className="card settings-card">
          <div className="card-head"><div><h2><Shield size={16} /> Security</h2></div></div>
          <div className="settings-list">
            <div><span>API Authentication</span><b className="text-green">Active (X-API-Key)</b></div>
            <div><span>CORS Policy</span><b>Restricted origins</b></div>
            <div><span>Rate Limiting</span><b>30/min default, 10/min expensive</b></div>
          </div>
        </div>

        <div className="card settings-card">
          <div className="card-head"><div><h2><Gauge size={16} /> API Limits</h2></div></div>
          <div className="settings-list">
            <div><span>Max Gemini Calls/min</span><b>5</b></div>
            <div><span>Max Weather Calls/min</span><b>10</b></div>
            <div><span>Cache TTL</span><b>600 seconds</b></div>
          </div>
        </div>

        <div className="card settings-card">
          <div className="card-head"><div><h2><Database size={16} /> Backend</h2></div></div>
          <div className="settings-list">
            <div><span>Database</span><b>SQLite (relocation.db)</b></div>
            <div><span>Villages Loaded</span><b>13</b></div>
            <div><span>Shelters Loaded</span><b>8</b></div>
            <div><span>Routes Loaded</span><b>12</b></div>
          </div>
        </div>

        <div className="card settings-card">
          <div className="card-head"><div><h2><Globe size={16} /> External APIs</h2></div></div>
          <div className="settings-list">
            <div><span>Weather API</span><b>Open-Meteo (free tier)</b></div>
            <div><span>AI Summaries</span><b>Gemini 2.5 Flash</b></div>
            <div><span>Graceful Degradation</span><b className="text-green">Enabled</b></div>
          </div>
        </div>
      </div>
    </div>
  );
}
