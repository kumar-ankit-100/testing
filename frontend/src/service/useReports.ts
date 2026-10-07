/**
 * Admin reporting dashboard hook (E7-S4): loads the dashboard on mount,
 * re-polls it on an interval, and exposes a manual refresh — so the
 * dashboard reflects whatever subscribers/CSRs/admins are doing
 * elsewhere in the app without requiring a full page reload.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";
import { getAdminDashboard } from "../api/reportsApi";
import type { AdminDashboardResponse } from "../types/api";

const POLL_INTERVAL_MS = 10_000;

export interface UseReportsResult {
  dashboard: AdminDashboardResponse | null;
  loading: boolean;
  error: string | null;
  lastUpdatedAt: Date | null;
  refresh: () => void;
}

export function useReports(): UseReportsResult {
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const cancelledRef = useRef(false);

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      const response = await getAdminDashboard();
      if (!cancelledRef.current) {
        setDashboard(response);
        setLastUpdatedAt(new Date());
      }
    } catch (err) {
      if (!cancelledRef.current) {
        setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
      }
    } finally {
      if (!cancelledRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    setLoading(true);
    void load();

    const intervalId = setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => {
      cancelledRef.current = true;
      clearInterval(intervalId);
    };
  }, [load]);

  const refresh = useCallback((): void => {
    setLoading(true);
    void load();
  }, [load]);

  return { dashboard, loading, error, lastUpdatedAt, refresh };
}
