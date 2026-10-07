/**
 * Plan change preview/commit API calls (E4-S4).
 *
 * API layer.
 */

import { apiFetch } from "./client";
import type {
  PlanChangeCommitResponse,
  PlanChangePreviewResponse,
  PlanChangeRequest,
} from "../types/api";

export async function previewPlanChange(
  subscriptionId: string,
  request: PlanChangeRequest,
): Promise<PlanChangePreviewResponse> {
  return apiFetch<PlanChangePreviewResponse>(
    `/api/subscriptions/${subscriptionId}/plan-change/preview`,
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function commitPlanChange(
  subscriptionId: string,
  request: PlanChangeRequest,
): Promise<PlanChangeCommitResponse> {
  return apiFetch<PlanChangeCommitResponse>(
    `/api/subscriptions/${subscriptionId}/plan-change/commit`,
    { method: "POST", body: JSON.stringify(request) },
  );
}
