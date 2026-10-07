/**
 * Admin reporting dashboard hook (E7-S4): loads the dashboard once on
 * mount and exposes loading/error state.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { getAdminDashboard } from "../api/reportsApi";
import type { AdminDashboardResponse } from "../types/api";

export interface UseReportsResult {
  dashboard: AdminDashboardResponse | null;
  loading: boolean;
  error: string | null;
}

export function useReports(): UseReportsResult {
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      try {
        const response = await getAdminDashboard();
        if (!cancelled) {
          setDashboard(response);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { dashboard, loading, error };
}
