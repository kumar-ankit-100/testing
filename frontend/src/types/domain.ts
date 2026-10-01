/**
 * Domain enums mirroring the backend Types layer (E3-S4; Role added E1-S6).
 *
 * Types layer — imports nothing else, per folder-structure.md.
 */

export type PlanType = "PREPAID" | "POSTPAID";

export type Role = "subscriber" | "csr" | "admin" | "dealer";
