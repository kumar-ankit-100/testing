/**
 * Domain enums mirroring the backend Types layer (E3-S4; Role added E1-S6).
 *
 * Types layer — imports nothing else, per folder-structure.md.
 */

export type PlanType = "PREPAID" | "POSTPAID";

export type Role = "subscriber" | "csr" | "admin" | "dealer";

/** Subscription lifecycle states (E2-S5), mirroring the backend FSM. */
export type SubscriberState =
  | "PENDING_KYC"
  | "ACTIVE"
  | "SUSPENDED"
  | "PORT_OUT_REQUESTED"
  | "PORTED_OUT"
  | "TERMINATED";
