/**
 * CSR override API calls (E6-S3).
 *
 * API layer.
 */

import { apiFetch } from "./client";
import type {
  OverrideActivationRequest,
  OverrideActivationResponse,
  OverridePlanChangeRequest,
  OverridePlanChangeResponse,
} from "../types/api";

export async function overrideActivation(
  subscriberId: string,
  request: OverrideActivationRequest,
): Promise<OverrideActivationResponse> {
  return apiFetch<OverrideActivationResponse>(
    `/api/csr/overrides/activation/${subscriberId}`,
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function overridePlanChange(
  subscriptionId: string,
  request: OverridePlanChangeRequest,
): Promise<OverridePlanChangeResponse> {
  return apiFetch<OverridePlanChangeResponse>(
    `/api/csr/overrides/plan-change/${subscriptionId}`,
    { method: "POST", body: JSON.stringify(request) },
  );
}
