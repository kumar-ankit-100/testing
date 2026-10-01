/**
 * API request/response DTOs matching specs/design/api-contracts.md
 * (E3-S4: plan catalog admin endpoints only — extended by every later UI
 * story as it adds its own endpoints' DTOs, per component-map.md).
 *
 * Types layer — imports only from ./domain.
 */

import type { PlanType, Role, SubscriberState } from "./domain";

/** Money fields are always JSON strings on the wire (e.g. "499.00"). */
export type DecimalString = string;

export interface PlanVersionTerms {
  validity_days: number;
  data_gb: number;
  sms_per_day: number;
}

export interface PlanVersionDto {
  plan_version_id: string;
  plan_id: string;
  plan_name: string;
  plan_type: PlanType;
  version_number: number;
  price: DecimalString;
  terms: PlanVersionTerms;
  published: boolean;
  created_at: string;
  published_at: string | null;
}

export interface PlanVersionListResponse {
  plans: PlanVersionDto[];
}

export interface CreatePlanVersionRequest {
  plan_id: string;
  plan_name: string;
  plan_type: PlanType;
  price: DecimalString;
  terms: PlanVersionTerms;
}

export interface CreatePlanVersionResponse {
  plan_version_id: string;
  plan_id: string;
  version_number: number;
  published: boolean;
}

export interface PublishPlanVersionResponse {
  plan_version_id: string;
  published: boolean;
  published_at: string;
}

export interface ApiErrorEnvelope {
  error: {
    reason_code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

/**
 * POST /api/auth/login (E1-S6). Staff login supplies username+password;
 * subscriber self-service supplies mobile_number only.
 */
export interface LoginRequest {
  username?: string;
  password?: string;
  mobile_number?: string;
}

export interface LoginResponse {
  access_token: string;
  role: Role;
  subscriber_id: string | null;
  expires_in: number;
}

/**
 * POST /api/subscribers/register and GET-style activation status
 * polling (E2-S5).
 */
export interface RegisterSubscriberRequest {
  mobile_number: string;
  identity_proof_ref: string;
  plan_type: PlanType;
}

export interface RegisterSubscriberResponse {
  subscriber_id: string;
  subscription_id: string;
  state: SubscriberState;
}

export interface ActivateSubscriberRequest {
  dealer_code: string;
}

export interface ActivateSubscriberResponse {
  subscriber_id: string;
  state: SubscriberState;
  activated_at: string;
}
