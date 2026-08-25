import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../api/client";

/**
 * Fetches aggregate dashboard overview.
 *
 * @returns {{ overview, loading, error, refetch }}
 */
export default function useDashboardOverview() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch("/dashboard/overview");
      setOverview(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  return { overview, loading, error, refetch: fetchOverview };
}
