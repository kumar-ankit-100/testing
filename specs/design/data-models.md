# TelcoLane — Data Models

All entities live in the `Types` layer (`backend/src/types/`) as typed dataclasses/pydantic models with zero imports from any other layer. Money fields are always `Decimal`; timestamps are UTC `datetime`. SQLite has no native decimal or enum type, so the Repository layer stores `Decimal` as canonical `TEXT` (`str(Decimal(...))`) and enums as `TEXT` with a `CHECK` constraint — this is a storage-layer detail, not a Types-layer concern.

Design note: `Subscriber` is the durable identity (mobile number + identity proof); `Subscription` is the lifecycle/plan entity tied to a subscriber. A single registration call creates one of each. `Subscription.mobile_number` is a denormalized copy of the owning `Subscriber.mobile_number`, needed so the partial-unique-active-mobile index (E2-S1 AC-2) can be declared directly on the `subscriptions` table.

---

## Subscriber

Identity/contact record created at registration.

| Field | Type | Constraints |
|---|---|---|
| `subscriber_id` | `str` (UUID) | PK |
| `mobile_number` | `str` | 10-digit numeric, not null |
| `identity_proof_ref` | `str` | not null; PII — masked in all logs |
| `created_at` | `datetime` | not null, UTC |

**Indexes**: `idx_subscriber_mobile` on `mobile_number` (lookup only — uniqueness is enforced on `Subscription`, not here, since a mobile number may re-register after a prior subscription reaches `TERMINATED`/`PORTED_OUT`).

**Example**:
```json
{ "subscriber_id": "sub_9f2a7c10", "mobile_number": "9876543210", "identity_proof_ref": "AADHAAR-XXXX-XXXX-1234", "created_at": "2026-09-30T09:00:00Z" }
```

---

## Subscription

Lifecycle + plan-linkage record. One `Subscriber` may have multiple `Subscription` rows over time (e.g. re-registering after an earlier one terminated), but at most one may be `state = ACTIVE` per `mobile_number`.

| Field | Type | Constraints |
|---|---|---|
| `subscription_id` | `str` (UUID) | PK |
| `subscriber_id` | `str` (UUID) | FK -> `Subscriber.subscriber_id`, not null |
| `mobile_number` | `str` | denormalized from `Subscriber`, not null |
| `plan_type` | `PlanType` enum (`PREPAID`, `POSTPAID`) | not null |
| `state` | `SubscriberState` enum | not null; see FSM below |
| `current_plan_version_id` | `str` (UUID) | FK -> `PlanVersion.plan_version_id`, nullable until activation |
| `dealer_code` | `str` | nullable until activation attempt |
| `created_at` | `datetime` | not null, UTC |
| `activated_at` | `datetime` | nullable |
| `updated_at` | `datetime` | not null, UTC, bumped on every state/plan change |

**Constraints**: `UNIQUE INDEX ux_subscription_mobile_active ON subscriptions(mobile_number) WHERE state = 'ACTIVE'` (partial unique index — this is the actual concurrency guard for NFR-07, not the service-layer FSM check, which is a secondary in-process guard).

**Indexes**: `idx_subscription_subscriber` on `subscriber_id`.

**FSM — `SubscriberState`**: `PENDING_KYC | ACTIVE | SUSPENDED | TERMINATED | PORT_OUT_REQUESTED | PORTED_OUT`.

Valid transition table (declarative, defined once in `Types`):

| From | To | Triggered by |
|---|---|---|
| `PENDING_KYC` | `ACTIVE` | activation success (E2-S3), or CSR override (E6-S2) |
| `ACTIVE` | `SUSPENDED` | suspend (E5-S2) |
| `SUSPENDED` | `ACTIVE` | resume (E5-S2) |
| `ACTIVE` | `PORT_OUT_REQUESTED` | port-out request (E5-S3) |
| `PORT_OUT_REQUESTED` | `ACTIVE` | port-out cancel within window (E5-S3) |
| `PORT_OUT_REQUESTED` | `PORTED_OUT` | port-out finalize after window (E5-S3) |
| `ACTIVE` | `TERMINATED` | CSR/admin account closure (E6-S5, E6-S6 — see system-design.md §5.9) |
| `SUSPENDED` | `TERMINATED` | CSR/admin account closure (E6-S5, E6-S6) |

Any pair not in this table raises `InvalidSubscriberStateException`. `TERMINATED` and `PORTED_OUT` are terminal — no outbound edges.

**Example**:
```json
{
  "subscription_id": "subn_1a2b3c", "subscriber_id": "sub_9f2a7c10", "mobile_number": "9876543210",
  "plan_type": "PREPAID", "state": "ACTIVE", "current_plan_version_id": "pv_77aa",
  "dealer_code": "DLR-001", "created_at": "2026-09-30T09:00:00Z",
  "activated_at": "2026-09-30T09:05:00Z", "updated_at": "2026-09-30T09:05:00Z"
}
```

---

## PlanVersion

Append-only-once-published catalog entry. `plan_id` groups all versions of "the same plan"; `version_number` increments per `plan_id`.

| Field | Type | Constraints |
|---|---|---|
| `plan_version_id` | `str` (UUID) | PK |
| `plan_id` | `str` | not null (stable identifier across versions) |
| `plan_name` | `str` | not null |
| `plan_type` | `PlanType` enum | not null |
| `version_number` | `int` | not null, >= 1, unique per `(plan_id, version_number)` |
| `price` | `Decimal` | not null, >= 0 |
| `terms` | `dict` (JSON) | not null |
| `published` | `bool` | not null, default `false` |
| `created_at` | `datetime` | not null, UTC |
| `published_at` | `datetime` | nullable; set exactly once, on publish |

**Constraints**: once `published = true`, no `UPDATE` is permitted on this row (enforced by repository — no `update` function exists for a published row — and by a DB `BEFORE UPDATE` trigger as defense-in-depth). `UNIQUE(plan_id, version_number)`.

**Indexes**: `idx_planversion_plan_published` on `(plan_id, published)` for `get_published_version` lookups.

**Example**:
```json
{ "plan_version_id": "pv_77aa", "plan_id": "plan_basic", "plan_name": "Basic Prepaid", "plan_type": "PREPAID", "version_number": 3, "price": "199.00", "terms": {"data_gb": 2, "validity_days": 28}, "published": true, "created_at": "2026-08-01T00:00:00Z", "published_at": "2026-08-01T00:05:00Z" }
```

---

## BillingRecord

Append-only. One row per committed plan change.

| Field | Type | Constraints |
|---|---|---|
| `billing_record_id` | `str` (UUID) | PK |
| `subscription_id` | `str` (UUID) | FK -> `Subscription.subscription_id`, not null |
| `from_plan_version_id` | `str` (UUID) | FK -> `PlanVersion.plan_version_id`, nullable (null on first activation billing) |
| `to_plan_version_id` | `str` (UUID) | FK -> `PlanVersion.plan_version_id`, not null |
| `pro_rata_amount` | `Decimal` | not null, >= 0 |
| `charges_total` | `Decimal` | not null, >= 0 (NFR-08 invariant) |
| `billing_period_start` | `date` | not null |
| `billing_period_end` | `date` | not null |
| `created_at` | `datetime` | not null, UTC |

**Constraints**: no `update`/`delete` repository function exists; a DB trigger blocks raw `UPDATE`/`DELETE` as defense-in-depth (E4-S1 AC-3).

**Indexes**: `idx_billing_subscription` on `subscription_id`.

**Example**:
```json
{ "billing_record_id": "bill_55f1", "subscription_id": "subn_1a2b3c", "from_plan_version_id": "pv_77aa", "to_plan_version_id": "pv_90cc", "pro_rata_amount": "42.35", "charges_total": "42.35", "billing_period_start": "2026-09-15", "billing_period_end": "2026-10-15", "created_at": "2026-09-30T10:00:00Z" }
```

---

## StateTransition

Append-only audit log of every FSM move.

| Field | Type | Constraints |
|---|---|---|
| `transition_id` | `str` (UUID) | PK |
| `subscription_id` | `str` (UUID) | FK -> `Subscription.subscription_id`, not null |
| `from_state` | `SubscriberState` enum | not null |
| `to_state` | `SubscriberState` enum | not null |
| `reason_code` | `str` | nullable (e.g. `CSR_OVERRIDE`; null for routine transitions) |
| `actor` | `str` | not null (`subscriber_id`, CSR/admin `user_id`, or `"system"`) |
| `created_at` | `datetime` | not null, UTC |

**Constraints**: no `update`/`delete` repository function exists (E5-S1 AC-1).

**Indexes**: `idx_transition_subscription_created` on `(subscription_id, created_at)` for chronological retrieval.

**Example**:
```json
{ "transition_id": "trn_001", "subscription_id": "subn_1a2b3c", "from_state": "PENDING_KYC", "to_state": "ACTIVE", "reason_code": null, "actor": "sub_9f2a7c10", "created_at": "2026-09-30T09:05:00Z" }
```

---

## PortOutEvent

Append-only (close = status update, never delete). Tracks the 7-day cooling period.

| Field | Type | Constraints |
|---|---|---|
| `port_out_event_id` | `str` (UUID) | PK |
| `subscription_id` | `str` (UUID) | FK -> `Subscription.subscription_id`, not null |
| `requested_at` | `datetime` | not null, UTC |
| `cooling_period_end_at` | `datetime` | not null, UTC; `requested_at + 7 days`, computed and stored at request time |
| `status` | `str` enum (`PENDING`, `CANCELLED_WITHIN_WINDOW`, `FINALIZED`) | not null, default `PENDING` |
| `closed_at` | `datetime` | nullable; set when status transitions away from `PENDING` |

**Constraints**: `get_active_port_out_event` returns the row with `status = 'PENDING'` for a subscription (at most one, enforced by the service layer refusing a second concurrent port-out request while one is `PENDING`).

**Indexes**: `idx_portout_subscription_status` on `(subscription_id, status)`.

**Example**:
```json
{ "port_out_event_id": "po_001", "subscription_id": "subn_1a2b3c", "requested_at": "2026-09-30T10:00:00Z", "cooling_period_end_at": "2026-10-07T10:00:00Z", "status": "PENDING", "closed_at": null }
```

---

## CSROverride

Append-only audit trail.

| Field | Type | Constraints |
|---|---|---|
| `override_id` | `str` (UUID) | PK |
| `subscription_id` | `str` (UUID) | FK -> `Subscription.subscription_id`, not null |
| `actor` | `str` | not null (CSR `user_id`) |
| `reason_code` | `str` | not null (E6-S1 AC-2) |
| `overridden_action` | `str` enum (`ACTIVATION`, `PLAN_CHANGE`) | not null |
| `original_rejection_reason` | `str` | not null (the reason code being overridden, e.g. `DEALER_INVALID`) |
| `created_at` | `datetime` | not null, UTC |

**Indexes**: `idx_override_subscription` on `subscription_id`.

**Example**:
```json
{ "override_id": "ovr_33x1", "subscription_id": "subn_1a2b3c", "actor": "csr_jane", "reason_code": "CSR_VERIFIED_MANUALLY", "overridden_action": "ACTIVATION", "original_rejection_reason": "DEALER_INVALID", "created_at": "2026-09-30T09:10:00Z" }
```

---

## DealerMaster

Seeded reference table for activation-time dealer-code validation. Not append-only (reference data), no dealer-facing CRUD UI.

| Field | Type | Constraints |
|---|---|---|
| `dealer_code` | `str` | PK |
| `dealer_name` | `str` | not null |
| `active` | `bool` | not null, default `true` |

**Seed data**: at least 5 valid codes plus the `DEALER-FAIL` sentinel (`active = false`), per E2-S1 AC-3.

**Example**:
```json
{ "dealer_code": "DLR-001", "dealer_name": "City Center Retail", "active": true }
```
```json
{ "dealer_code": "DEALER-FAIL", "dealer_name": "Stub Failure Sentinel", "active": false }
```

---

## User (auth entity)

Backs `POST /api/auth/login`. Staff (`csr`, `admin`, `dealer`) rows are seeded; `subscriber` rows are created implicitly by the login/registration flow.

| Field | Type | Constraints |
|---|---|---|
| `user_id` | `str` (UUID) | PK |
| `role` | `Role` enum (`subscriber`, `csr`, `admin`, `dealer`) | not null |
| `username` | `str` | nullable (staff only), unique when present |
| `password_hash` | `str` | nullable (staff only) |
| `mobile_number` | `str` | nullable (subscriber only), unique when present |
| `subscriber_id` | `str` (UUID) | FK -> `Subscriber.subscriber_id`, nullable (set once registration completes) |
| `created_at` | `datetime` | not null, UTC |

**Indexes**: `idx_user_username`, `idx_user_mobile` (both unique-when-not-null).

**Example**:
```json
{ "user_id": "usr_csr_01", "role": "csr", "username": "csr_jane", "password_hash": "<bcrypt>", "mobile_number": null, "subscriber_id": null, "created_at": "2026-01-01T00:00:00Z" }
```

---

## Shared Enums (Types layer)

- `SubscriberState`: `PENDING_KYC | ACTIVE | SUSPENDED | TERMINATED | PORT_OUT_REQUESTED | PORTED_OUT`
- `PlanType`: `PREPAID | POSTPAID`
- `Role`: `subscriber | csr | admin | dealer`
- `ReasonCode`: `KYC_UNVERIFIED | DEALER_INVALID | MNP_FAILED | MIN_TENURE_NOT_MET | SUBSCRIPTION_SUSPENDED | COOLING_PERIOD_NOT_ELAPSED | INVALID_STATE_TRANSITION | ALREADY_ACTIVE | DUPLICATE_ACTIVE_MOBILE | MISSING_OVERRIDE_REASON | PLAN_VERSION_IMMUTABLE | VALIDATION_ERROR | UNAUTHENTICATED | FORBIDDEN | NOT_FOUND | RATE_LIMITED`

## Relationships

```
Subscriber 1 ──< N Subscription
Subscription N ──> 1 PlanVersion        (current_plan_version_id)
Subscription 1 ──< N BillingRecord
Subscription 1 ──< N StateTransition
Subscription 1 ──< N PortOutEvent
Subscription 1 ──< N CSROverride
Subscriber   0..1 ──> 1 User            (subscriber_id, once registered)
PlanVersion  N ──> 1 (plan_id group)    (self-referential version chain, not an FK)
```
