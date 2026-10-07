/**
 * Suspend/resume/port-out/terminate API calls (E5-S4, E6-S6).
 *
 * API layer.
 */

import { apiFetch } from "./client";
import type {
  LifecycleStateResponse,
  PortOutEventResponse,
  TerminateRequest,
} from "../types/api";

export async function suspendSubscription(
  subscriptionId: string,
): Promise<LifecycleStateResponse> {
  return apiFetch<LifecycleStateResponse>(`/api/subscriptions/${subscriptionId}/suspend`, {
    method: "POST",
  });
}

export async function resumeSubscription(
  subscriptionId: string,
): Promise<LifecycleStateResponse> {
  return apiFetch<LifecycleStateResponse>(`/api/subscriptions/${subscriptionId}/resume`, {
    method: "POST",
  });
}

export async function requestPortOut(subscriptionId: string): Promise<PortOutEventResponse> {
  return apiFetch<PortOutEventResponse>(
    `/api/subscriptions/${subscriptionId}/port-out/request`,
    { method: "POST" },
  );
}

export async function cancelPortOut(subscriptionId: string): Promise<LifecycleStateResponse> {
  return apiFetch<LifecycleStateResponse>(
    `/api/subscriptions/${subscriptionId}/port-out/cancel`,
    { method: "POST" },
  );
}

export async function terminateSubscription(
  subscriptionId: string,
  request: TerminateRequest,
): Promise<LifecycleStateResponse> {
  return apiFetch<LifecycleStateResponse>(`/api/subscriptions/${subscriptionId}/terminate`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}
