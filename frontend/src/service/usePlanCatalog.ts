/**
 * React hook composing planApi calls into UI-facing state (E3-S4).
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useEffect, useState } from "react";

import { createPlanVersion, listPlanVersions, publishPlanVersion } from "../api/planApi";
import type { CreatePlanVersionRequest, PlanVersionDto } from "../types/api";

export interface UsePlanCatalogResult {
  versions: PlanVersionDto[];
  loading: boolean;
  error: string | null;
  createDraft: (request: CreatePlanVersionRequest) => Promise<boolean>;
  publishDraft: (planVersionId: string) => Promise<void>;
}

/** All versions for a single plan_id, ascending by version_number. */
export function usePlanCatalog(planId: string): UsePlanCatalogResult {
  const [versions, setVersions] = useState<PlanVersionDto[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const all = await listPlanVersions();
      const forPlan = all
        .filter((version) => version.plan_id === planId)
        .sort((a, b) => a.version_number - b.version_number);
      setVersions(forPlan);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load plan versions");
    } finally {
      setLoading(false);
    }
  }, [planId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const createDraft = useCallback(
    async (request: CreatePlanVersionRequest): Promise<boolean> => {
      setError(null);
      try {
        await createPlanVersion(request);
        await refresh();
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to create draft version";
        setError(message);
        return false;
      }
    },
    [refresh],
  );

  const publishDraft = useCallback(
    async (planVersionId: string): Promise<void> => {
      setError(null);
      try {
        await publishPlanVersion(planVersionId);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to publish draft version");
      }
    },
    [refresh],
  );

  return { versions, loading, error, createDraft, publishDraft };
}
