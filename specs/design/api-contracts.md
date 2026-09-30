# TelcoLane — API Contracts

Base URL (dev): `http://localhost:8000`. All request/response bodies are JSON. All money fields are serialized as JSON strings (e.g. `"499.00"`) to preserve Decimal precision — clients must not parse them as IEEE floats.

## Conventions

- **Auth header**: `Authorization: Bearer <token>` on every route except `GET /health`.
- **Roles**: `subscriber`, `csr`, `admin`, `dealer`. A route's "Auth" row lists which role(s) may call it; `subscriber (self)` means the token's `subscriber_id` claim must equal the resource's owning subscriber, or the call receives `403`.
- **Error shape** (all 4xx/5xx):
  ```json
  { "error": { "reason_code": "MIN_TENURE_NOT_MET", "message": "Subscription has not met the minimum tenure period.", "details": {} } }
  ```
- **Reason codes** (`error.reason_code`): `UNAUTHENTICATED`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`, `DUPLICATE_ACTIVE_MOBILE`, `KYC_UNVERIFIED`, `DEALER_INVALID`, `MNP_FAILED`, `INVALID_STATE_TRANSITION`, `ALREADY_ACTIVE`, `MIN_TENURE_NOT_MET`, `SUBSCRIPTION_SUSPENDED`, `COOLING_PERIOD_NOT_ELAPSED`, `PLAN_VERSION_IMMUTABLE`, `MISSING_OVERRIDE_REASON`.
- **Rate limits**: enforced per bearer token (or per source IP for unauthenticated `/health`) via a fixed window.

| Caller class | Limit |
|---|---|
| `subscriber` self-service routes | 60 requests/minute |
| `csr` / `admin` staff routes | 300 requests/minute |
| `POST /api/auth/login` | 10 requests/minute per IP (brute-force guard) |
| `GET /health` | unlimited |

A limit breach returns `HTTP 429` with `{"error": {"reason_code": "RATE_LIMITED", "message": "..."}}`.

Each endpoint below is documented as: **Method & Path**, **Auth**, **Request**, **Response (success)**, **Response (error)**.

---

## Health

### `GET /health`
- **Auth**: none.
- **Request**: no params.
- **Response 200**:
  ```json
  { "status": "ok" }
  ```

---

## Auth

### `POST /api/auth/login`
Stubbed authentication. Staff (`csr`/`admin`) log in with seeded credentials. Subscribers self-serve with just a mobile number (no OTP is real — MNP/KYC are stubbed per E1-S2); dealer accounts exist only for authorization-test/context purposes and are seeded like staff.

- **Auth**: none.
- **Request body** (staff):
  ```json
  { "username": "csr_jane", "password": "stubbed-in-dev" }
  ```
- **Request body** (subscriber self-service):
  ```json
  { "mobile_number": "9876543210" }
  ```
- **Response 200**:
  ```json
  {
    "access_token": "<jwt>",
    "role": "subscriber",
    "subscriber_id": "sub_9f2a...",
    "expires_in": 3600
  }
  ```
  `subscriber_id` is `null` when the mobile number has no `Subscriber` row yet (pre-registration token); `POST /api/subscribers/register` then creates the row and returns a fresh token with `subscriber_id` populated.
- **Response 401**: invalid staff credentials → `{"error": {"reason_code": "UNAUTHENTICATED", ...}}`.

---

## Registration & Activation (E2)

### `POST /api/subscribers/register`
- **Auth**: `subscriber` (pre-registration token, `subscriber_id: null`, from `/api/auth/login`).
- **Request body**:
  ```json
  {
    "mobile_number": "9876543210",
    "identity_proof_ref": "AADHAAR-XXXX-XXXX-1234",
    "plan_type": "PREPAID"
  }
  ```
- **Response 201**:
  ```json
  {
    "subscriber_id": "sub_9f2a...",
    "subscription_id": "subn_1a2b...",
    "state": "PENDING_KYC",
    "access_token": "<jwt with subscriber_id populated>"
  }
  ```
- **Response 409**: mobile number already has an ACTIVE subscription → `reason_code: DUPLICATE_ACTIVE_MOBILE`.
- **Response 422**: malformed mobile number → `reason_code: VALIDATION_ERROR` (rejected before any DB write).

### `POST /api/subscribers/{subscriber_id}/activate`
- **Auth**: `subscriber (self)`.
- **Request body**:
  ```json
  { "dealer_code": "DLR-001" }
  ```
  (KYC and MNP outcomes are read from the deterministic `Config` stub flags, not from the request body.)
- **Response 200**:
  ```json
  { "subscriber_id": "sub_9f2a...", "state": "ACTIVE", "activated_at": "2026-09-30T10:00:00Z" }
  ```
- **Response 422**: activation rule failed → `reason_code` one of `KYC_UNVERIFIED`, `DEALER_INVALID`, `MNP_FAILED`; subscription remains `PENDING_KYC`.
- **Response 409**: subscription not in `PENDING_KYC` (e.g. already `ACTIVE`) → `reason_code: ALREADY_ACTIVE` or `INVALID_STATE_TRANSITION`.

### `GET /api/subscribers/{subscriber_id}`
- **Auth**: `subscriber (self)`, `csr`, `admin`.
- **Response 200**:
  ```json
  {
    "subscriber_id": "sub_9f2a...",
    "mobile_number": "******3210",
    "subscription": {
      "subscription_id": "subn_1a2b...",
      "state": "ACTIVE",
      "plan_type": "PREPAID",
      "current_plan_version_id": "pv_77...",
      "activated_at": "2026-09-30T10:00:00Z"
    }
  }
  ```
  `mobile_number` is masked in the same way logs are masked (last 4 digits visible) for any caller other than the owning subscriber; `csr`/`admin` callers receive the unmasked value since they are authorized staff performing support actions.

---

## Plan Catalog (E3)

### `GET /api/plans`
Published plans only — used by registration/plan-change UIs.
- **Auth**: any authenticated role.
- **Response 200**:
  ```json
  {
    "plans": [
      { "plan_id": "plan_basic", "plan_version_id": "pv_77...", "plan_name": "Basic Prepaid", "plan_type": "PREPAID", "version_number": 3, "price": "199.00", "published": true }
    ]
  }
  ```

### `POST /api/admin/plans`
Creates a new draft version (version 1 for a brand-new plan, or the next version number for an existing `plan_id`).
- **Auth**: `admin`.
- **Request body**:
  ```json
  { "plan_id": "plan_basic", "plan_name": "Basic Prepaid", "plan_type": "PREPAID", "price": "199.00", "terms": {"data_gb": 2, "validity_days": 28} }
  ```
- **Response 201**:
  ```json
  { "plan_version_id": "pv_78...", "plan_id": "plan_basic", "version_number": 4, "published": false }
  ```

### `POST /api/admin/plans/{plan_version_id}/publish`
- **Auth**: `admin`.
- **Response 200**:
  ```json
  { "plan_version_id": "pv_78...", "published": true, "published_at": "2026-09-30T10:00:00Z" }
  ```

### `PUT /api/admin/plans/{plan_version_id}`
Edits a **draft** version's fields.
- **Auth**: `admin`.
- **Request body**: any subset of `{price, terms, plan_name}`.
- **Response 200**: updated draft version.
- **Response 409**: version already published → `reason_code: PLAN_VERSION_IMMUTABLE`.

### `GET /api/admin/plans`
Full version history, including superseded/unpublished versions.
- **Auth**: `admin`.
- **Response 200**:
  ```json
  {
    "plans": [
      { "plan_version_id": "pv_10...", "plan_id": "plan_basic", "version_number": 1, "published": false, "price": "149.00" },
      { "plan_version_id": "pv_77...", "plan_id": "plan_basic", "version_number": 3, "published": true, "price": "199.00" }
    ]
  }
  ```

---

## Plan Change (E4)

### `POST /api/subscriptions/{subscription_id}/plan-change/preview`
No mutation.
- **Auth**: `subscriber (self)`, `csr`.
- **Request body**:
  ```json
  { "target_plan_version_id": "pv_90..." }
  ```
- **Response 200**:
  ```json
  { "pro_rata_amount": "42.35", "charges_total": "42.35", "target_plan_version_id": "pv_90...", "billing_period_end": "2026-10-15" }
  ```
- **Response 409**: subscription is `SUSPENDED` → `reason_code: SUBSCRIPTION_SUSPENDED`.
- **Response 422**: below minimum tenure → `reason_code: MIN_TENURE_NOT_MET`.

### `POST /api/subscriptions/{subscription_id}/plan-change/commit`
- **Auth**: `subscriber (self)`, `csr`.
- **Request body**: same as preview.
- **Response 200**:
  ```json
  { "billing_record_id": "bill_55...", "new_plan_version_id": "pv_90...", "pro_rata_amount": "42.35" }
  ```
- **Response 422**: `reason_code: MIN_TENURE_NOT_MET`.
- **Response 409**: `reason_code: SUBSCRIPTION_SUSPENDED`.
- **Response 403**: subscriber calling for a subscription not their own.

### `GET /api/subscriptions/{subscription_id}/billing-records`
- **Auth**: `subscriber (self)`, `csr`, `admin`.
- **Response 200**:
  ```json
  { "billing_records": [ { "billing_record_id": "bill_55...", "pro_rata_amount": "42.35", "charges_total": "42.35", "created_at": "2026-09-30T10:00:00Z" } ] }
  ```

---

## Suspend / Resume / Port-Out (E5)

### `POST /api/subscriptions/{subscription_id}/suspend`
- **Auth**: `subscriber (self)`, `csr`.
- **Response 200**: `{ "subscription_id": "subn_1a2b...", "state": "SUSPENDED" }`
- **Response 409**: not `ACTIVE` → `reason_code: INVALID_STATE_TRANSITION`.

### `POST /api/subscriptions/{subscription_id}/resume`
- **Auth**: `subscriber (self)`, `csr`.
- **Response 200**: `{ "subscription_id": "subn_1a2b...", "state": "ACTIVE" }`
- **Response 409**: not `SUSPENDED` → `reason_code: INVALID_STATE_TRANSITION`.

### `POST /api/subscriptions/{subscription_id}/port-out`
- **Auth**: `subscriber (self)`, `csr`.
- **Response 200**:
  ```json
  { "subscription_id": "subn_1a2b...", "state": "PORT_OUT_REQUESTED", "cooling_period_end_at": "2026-10-07T10:00:00Z" }
  ```
- **Response 409**: not `ACTIVE` → `reason_code: INVALID_STATE_TRANSITION`.

### `POST /api/subscriptions/{subscription_id}/port-out/cancel`
- **Auth**: `subscriber (self)`, `csr`.
- **Response 200**: `{ "subscription_id": "subn_1a2b...", "state": "ACTIVE" }`
- **Response 409**: no active port-out event, or window already elapsed and finalized → `reason_code: INVALID_STATE_TRANSITION`.

### `POST /api/subscriptions/{subscription_id}/port-out/finalize`
- **Auth**: `subscriber (self)`, `csr`.
- **Response 200**: `{ "subscription_id": "subn_1a2b...", "state": "PORTED_OUT" }`
- **Response 422**: cooling period not yet elapsed → `reason_code: COOLING_PERIOD_NOT_ELAPSED`.

### `POST /api/subscriptions/{subscription_id}/terminate`
CSR/admin-only account closure, independent of the port-out flow (E6-S5, E6-S6).
- **Auth**: `csr`, `admin`.
- **Request body**:
  ```json
  { "reason_code": "FRAUD_SUSPECTED" }
  ```
- **Response 200**:
  ```json
  { "subscription_id": "subn_1a2b...", "state": "TERMINATED" }
  ```
- **Response 409**: not `ACTIVE`/`SUSPENDED` → `reason_code: INVALID_STATE_TRANSITION`.
- **Response 422**: missing `reason_code` → `reason_code: VALIDATION_ERROR` (rejected before any write).
- **Response 403**: non-CSR/non-admin caller.

### `GET /api/subscriptions/{subscription_id}/state-transitions`
- **Auth**: `subscriber (self)`, `csr`, `admin`.
- **Response 200**:
  ```json
  { "transitions": [ { "from_state": "ACTIVE", "to_state": "PORT_OUT_REQUESTED", "reason_code": null, "actor": "sub_9f2a...", "created_at": "2026-09-30T10:00:00Z" } ] }
  ```

---

## CSR Exception Queue & Overrides (E6)

### `GET /api/csr/exceptions`
- **Auth**: `csr`.
- **Response 200**:
  ```json
  {
    "exceptions": [
      { "subscriber_id": "sub_9f2a...", "subscription_id": "subn_1a2b...", "rejected_action": "ACTIVATION", "reason_code": "DEALER_INVALID", "rejected_at": "2026-09-30T09:00:00Z" }
    ]
  }
  ```

### `POST /api/csr/exceptions/{subscription_id}/override`
- **Auth**: `csr`.
- **Request body**:
  ```json
  { "reason_code": "CSR_VERIFIED_MANUALLY", "action": "ACTIVATION" }
  ```
- **Response 200**:
  ```json
  { "subscription_id": "subn_1a2b...", "state": "ACTIVE", "override_id": "ovr_33..." }
  ```
- **Response 422**: missing `reason_code` → `reason_code: MISSING_OVERRIDE_REASON` (rejected before any write).
- **Response 403**: non-CSR caller.

### `GET /api/subscriptions/{subscription_id}/csr-overrides`
- **Auth**: `csr`, `admin`.
- **Response 200**:
  ```json
  { "overrides": [ { "override_id": "ovr_33...", "actor": "csr_jane", "reason_code": "CSR_VERIFIED_MANUALLY", "overridden_action": "ACTIVATION", "created_at": "2026-09-30T09:05:00Z" } ] }
  ```

---

## Admin Reporting (E7)

### `GET /api/admin/reports/activation-funnel`
- **Auth**: `admin`.
- **Query params**: `from` (date, optional), `to` (date, optional).
- **Response 200**:
  ```json
  {
    "stages": [
      { "stage": "REGISTERED", "count": 500 },
      { "stage": "KYC_PASSED", "count": 420 },
      { "stage": "DEALER_PASSED", "count": 400 },
      { "stage": "MNP_PASSED", "count": 390 },
      { "stage": "ACTIVATED", "count": 390 }
    ]
  }
  ```

### `GET /api/admin/reports/churn`
- **Auth**: `admin`.
- **Response 200**:
  ```json
  { "monthly": [ { "month": "2026-08", "churn_rate": "0.0421" } ] }
  ```

### `GET /api/admin/reports/plan-mix`
- **Auth**: `admin`.
- **Response 200**:
  ```json
  { "plans": [ { "plan_id": "plan_basic", "plan_name": "Basic Prepaid", "percentage": "62.5" } ] }
  ```

### `GET /api/admin/reports/arpu`
- **Auth**: `admin`.
- **Response 200**:
  ```json
  { "stubbed": true, "monthly": [ { "month": "2026-08", "arpu": "312.40" } ] }
  ```
