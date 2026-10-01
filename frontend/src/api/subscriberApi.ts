/**
 * Registration + activation API calls (E2-S5).
 *
 * API layer — the only module besides client.ts that talks to the
 * network for these endpoints.
 */

import { apiFetch } from "./client";
import type {
  ActivateSubscriberRequest,
  ActivateSubscriberResponse,
  RegisterSubscriberRequest,
  RegisterSubscriberResponse,
} from "../types/api";

export async function registerSubscriber(
  request: RegisterSubscriberRequest,
): Promise<RegisterSubscriberResponse> {
  return apiFetch<RegisterSubscriberResponse>("/api/subscribers/register", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function activateSubscriber(
  subscriberId: string,
  request: ActivateSubscriberRequest,
): Promise<ActivateSubscriberResponse> {
  return apiFetch<ActivateSubscriberResponse>(
    `/api/subscribers/${subscriberId}/activate`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}
