import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../api/client";

/**
 * Fetches the full village list with optional filters.
 *
 * @param {{ state?: string, min_risk?: number }} filters
 * @returns {{ villages, count, loading, error, refetch }}
 */
export default function useVillages(filters = {}) {
  const [villages, setVillages] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchVillages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filters.state) params.set("state", filters.state);
      if (filters.min_risk != null) params.set("min_risk", String(filters.min_risk));
      const qs = params.toString();
      const data = await apiFetch(`/villages${qs ? `?${qs}` : ""}`);
      setVillages(data.villages || []);
      setCount(data.count || 0);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [filters.state, filters.min_risk]);

  useEffect(() => {
    fetchVillages();
  }, [fetchVillages]);

  return { villages, count, loading, error, refetch: fetchVillages };
}
