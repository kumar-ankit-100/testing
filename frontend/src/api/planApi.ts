/**
 * Plan catalog admin API calls (E3-S4).
 *
 * API layer — the only module besides client.ts that talks to the network
 * for this story's endpoints.
 */

import { apiFetch } from "./client";
import type {
  CreatePlanVersionRequest,
  CreatePlanVersionResponse,
  PlanVersionDto,
  PlanVersionListResponse,
  PublishPlanVersionResponse,
} from "../types/api";

export async function listPlanVersions(): Promise<PlanVersionDto[]> {
  const response = await apiFetch<PlanVersionListResponse>("/api/admin/plans");
  return response.plans;
}

/** GET /api/plans: the current published version of every plan_id, open
 * to any authenticated role — unlike listPlanVersions above, which is
 * admin-only and includes drafts/superseded versions. Subscribers use
 * this to browse plans to pick a plan-change target. */
export async function listPublishedPlans(): Promise<PlanVersionDto[]> {
  const response = await apiFetch<PlanVersionListResponse>("/api/plans");
  return response.plans;
}

export async function createPlanVersion(
  request: CreatePlanVersionRequest,
): Promise<CreatePlanVersionResponse> {
  return apiFetch<CreatePlanVersionResponse>("/api/admin/plans", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function publishPlanVersion(
  planVersionId: string,
): Promise<PublishPlanVersionResponse> {
  return apiFetch<PublishPlanVersionResponse>(`/api/admin/plans/${planVersionId}/publish`, {
    method: "POST",
  });
}
