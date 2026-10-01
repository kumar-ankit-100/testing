/**
 * API request/response DTOs matching specs/design/api-contracts.md
 * (E3-S4: plan catalog admin endpoints only — extended by every later UI
 * story as it adds its own endpoints' DTOs, per component-map.md).
 *
 * Types layer — imports only from ./domain.
 */

import type { PlanType, Role } from "./domain";

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
