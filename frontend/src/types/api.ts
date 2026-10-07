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
 * POST /api/auth/register-staff: dynamic CSR/admin account creation.
 * Dealer is intentionally excluded — it has no dealer-facing UI
 * anywhere in this app (specs/design/system-design.md), so there is
 * nowhere for a self-registered dealer account to log in to. The
 * backend still accepts "dealer" (it's a valid Role for authorization
 * tests and seed data), this app's UI just never offers it.
 */
export interface RegisterStaffRequest {
  username: string;
  password: string;
  role: "csr" | "admin";
}

export interface RegisterStaffResponse {
  user_id: string;
  username: string;
  role: string;
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
  access_token: string;
}

export interface ActivateSubscriberRequest {
  dealer_code: string;
}

export interface ActivateSubscriberResponse {
  subscriber_id: string;
  state: SubscriberState;
  activated_at: string;
}

/** Suspend/resume/terminate (E5-S4, E6-S6). */
export interface LifecycleStateResponse {
  subscription_id: string;
  state: SubscriberState;
}

/** Port-out request/finalize (E5-S4). */
export interface PortOutEventResponse {
  port_out_event_id: string;
  subscription_id: string;
  requested_at: string;
  cooling_period_end_at: string;
  status: "PENDING" | "CANCELLED_WITHIN_WINDOW" | "FINALIZED";
}

export interface TerminateRequest {
  reason_code: string;
}

/** Plan change preview/commit (E4-S4). */
export interface PlanChangeRequest {
  target_plan_version_id: string;
}

export interface PlanChangePreviewResponse {
  pro_rata_amount: DecimalString;
}

export interface PlanChangeCommitResponse {
  billing_record_id: string;
  subscription_id: string;
  from_plan_version_id: string | null;
  to_plan_version_id: string;
  pro_rata_amount: DecimalString;
  billing_period_start: string;
  billing_period_end: string;
}

/** Admin reporting dashboard (E7-S3). */
export interface AdminDashboardResponse {
  activation_funnel: Record<string, number>;
  plan_mix: Record<string, number>;
  plan_mix_percentages: Record<string, DecimalString>;
  churn: Record<string, DecimalString>;
  arpu_trend: Record<string, DecimalString>;
  metadata: { arpu_trend_is_stubbed: boolean; arpu_trend_note: string };
}

/** CSR override API (E6-S3). */
export interface OverrideActivationRequest {
  dealer_code: string;
  reason_code: string;
  original_rejection_reason: string;
}

export interface OverrideActivationResponse {
  subscriber_id: string;
  state: SubscriberState;
}

export interface OverridePlanChangeRequest {
  target_plan_version_id: string;
  reason_code: string;
  original_rejection_reason: string;
}

export interface OverridePlanChangeResponse {
  billing_record_id: string;
  subscription_id: string;
  pro_rata_amount: DecimalString;
}
