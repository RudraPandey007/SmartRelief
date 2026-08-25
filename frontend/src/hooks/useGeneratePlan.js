import { useState, useCallback } from "react";
import { apiFetch } from "../api/client";

/**
 * Fetches a relocation plan for any village on demand (not on mount).
 *
 * @returns {{ plan, loading, error, generatePlan }}
 */
export default function useGeneratePlan() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generatePlan = useCallback(async (villageId) => {
    if (!villageId) return;
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      const data = await apiFetch("/relocation/generate-plan", {
        method: "POST",
        body: JSON.stringify({
          village_id: villageId,
          search_radius_km: 120,
        }),
      });
      setPlan(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearPlan = useCallback(() => {
    setPlan(null);
    setError(null);
  }, []);

  return { plan, loading, error, generatePlan, clearPlan };
}
