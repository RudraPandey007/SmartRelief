import { useState, useCallback } from "react";
import { apiFetch } from "../api/client";

/**
 * Manages what-if simulation state.
 *
 * Slider defaults represent 0–100 % display values.
 * API expects occupancy_percent / road_accessibility_percent as 0.0–1.0 floats
 * and rainfall_multiplier as a 0.1–10.0 multiplier.
 *
 * @param {string} villageId
 * @returns {{ simulated, sliders, setSlider, runSimulation, resetSimulation, simResult, simLoading, simError }}
 */
export default function useSimulation(villageId = "V001") {
  // Display values (0-100 for slider thumbs)
  const [sliders, setSliders] = useState({
    rainfall_mm: 58,       // mapped to multiplier: 0.1 + (value/100)*9.9
    occupancy_pct: 42,     // mapped to API: value / 100
    road_access_pct: 78,   // mapped to API: value / 100
  });

  const [simulated, setSimulated] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState(null);

  const updateSlider = useCallback((key, value) => {
    setSliders((prev) => ({ ...prev, [key]: Number(value) }));
  }, []);

  const runSimulation = useCallback(async () => {
    setSimLoading(true);
    setSimError(null);
    try {
      const rainfallMultiplier = 0.1 + (sliders.rainfall_mm / 100) * 9.9;
      const occupancy = sliders.occupancy_pct / 100;
      const roadAccess = sliders.road_access_pct / 100;

      const data = await apiFetch("/simulation/run", {
        method: "POST",
        body: JSON.stringify({
          village_id: villageId,
          overrides: {
            rainfall_multiplier: Math.round(rainfallMultiplier * 100) / 100,
            occupancy_percent: Math.round(occupancy * 100) / 100,
            road_accessibility_percent: Math.round(roadAccess * 100) / 100,
          },
          search_radius_km: 120,
        }),
      });

      setSimResult(data);
      setSimulated(true);
    } catch (err) {
      setSimError(err);
      setSimulated(false);
    } finally {
      setSimLoading(false);
    }
  }, [villageId, sliders]);

  const resetSimulation = useCallback(() => {
    setSimResult(null);
    setSimulated(false);
    setSimError(null);
  }, []);

  return {
    simulated,
    sliders,
    setSlider: updateSlider,
    runSimulation,
    resetSimulation,
    simResult,
    simLoading,
    simError,
  };
}
