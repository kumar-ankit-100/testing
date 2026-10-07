/**
 * Published plan catalog hook: loads the current published version of
 * every plan_id (GET /api/plans), for a subscriber to pick a
 * plan-change target from a real dropdown instead of pasting a raw
 * plan_version_id.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { listPublishedPlans } from "../api/planApi";
import type { PlanVersionDto } from "../types/api";

export interface UsePublishedPlansResult {
  plans: PlanVersionDto[];
  loading: boolean;
  error: string | null;
}

export function usePublishedPlans(): UsePublishedPlansResult {
  const [plans, setPlans] = useState<PlanVersionDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load(): Promise<void> {
      try {
        const response = await listPublishedPlans();
        if (!cancelled) {
          setPlans(response);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load plans");
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

  return { plans, loading, error };
}
