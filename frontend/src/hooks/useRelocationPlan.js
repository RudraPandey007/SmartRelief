import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../api/client";

/**
 * Fetches a relocation plan for the given village.
 *
 * @param {string} villageId – village to plan for (default "V001")
 * @returns {{ plan, loading, error, refetch }}
 */
export default function useRelocationPlan(villageId = "V001") {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPlan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch("/relocation/generate-plan", {
        method: "POST",
        body: JSON.stringify({
          village_id: villageId,
          search_radius_km: 120,
          weights: {
            safety: 0.25,
            capacity: 0.2,
            route: 0.15,
            healthcare: 0.15,
            water: 0.1,
            vulnerability_fit: 0.1,
            distance: 0.05,
          },
        }),
      });
      setPlan(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [villageId]);

  useEffect(() => {
    fetchPlan();
  }, [fetchPlan]);

  return { plan, loading, error, refetch: fetchPlan };
}
