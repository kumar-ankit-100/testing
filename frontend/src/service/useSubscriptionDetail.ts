/**
 * Subscriber dashboard data hook: loads the subscriber's own
 * subscription detail (GET /api/subscribers/{id}/subscription) and
 * re-polls it on an interval, same live-dashboard pattern as
 * useReports.ts — so the dashboard reflects a dealer/CSR override,
 * plan change, suspend/resume, or port-out made elsewhere without a
 * full page reload. Exposes a manual refresh too.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";
import { getSubscriptionDetail } from "../api/subscriberApi";
import type { SubscriptionDetailResponse } from "../types/api";

const POLL_INTERVAL_MS = 10_000;

export interface UseSubscriptionDetailResult {
  detail: SubscriptionDetailResponse | null;
  loading: boolean;
  error: string | null;
  lastUpdatedAt: Date | null;
  refresh: () => void;
}

export function useSubscriptionDetail(subscriberId: string): UseSubscriptionDetailResult {
  const [detail, setDetail] = useState<SubscriptionDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const cancelledRef = useRef(false);

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      const response = await getSubscriptionDetail(subscriberId);
      if (!cancelledRef.current) {
        setDetail(response);
        setLastUpdatedAt(new Date());
      }
    } catch (err) {
      if (!cancelledRef.current) {
        setError(err instanceof ApiError ? err.message : "Failed to load subscription");
      }
    } finally {
      if (!cancelledRef.current) {
        setLoading(false);
      }
    }
  }, [subscriberId]);

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

  return { detail, loading, error, lastUpdatedAt, refresh };
}
