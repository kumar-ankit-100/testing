# Feature Spec — Registration & Rule-Based Activation (AC-01, AC-02, AC-08)

Subscriber self-registration and rule-based activation gated on stubbed KYC, dealer-code, and MNP checks.

## Acceptance Criteria

**AC-01.1** — Given a valid mobile number, identity-proof reference, and plan type, when a subscriber registers, then a subscription is created in `PENDING_KYC` state.
*Test:* `backend/tests/integration/test_subscriber_api.py::test_register_with_valid_input_returns_201_pending_kyc`

**AC-01.2** — Given a mobile number that already has an ACTIVE subscription, when registration is attempted again, then it is rejected with HTTP 409 / `DUPLICATE_ACTIVE_MOBILE`, enforced by a partial unique index at the DB level (NFR-08), not just an application-level check.
*Test:* `test_subscriber_api.py::test_register_duplicate_active_mobile_returns_409`

**AC-08.1** — Given KYC-verified, a valid dealer code, and MNP success, when activation is attempted, then the subscription transitions `PENDING_KYC → ACTIVE` via the shared FSM, and an append-only `StateTransition` row is written.
*Test:* `test_subscriber_api.py::test_activate_with_all_flags_passing_returns_200_active`

**AC-08.2** — Given an unverified KYC flag, an invalid/`DEALER-FAIL` dealer code, or an MNP failure, when activation is attempted, then it is rejected with HTTP 422 and the specific reason code (`KYC_UNVERIFIED` / `DEALER_INVALID` / `MNP_FAILED`); the subscription remains `PENDING_KYC`.
*Test:* `test_subscriber_api.py::test_activate_with_dealer_fail_sentinel_returns_422_with_reason_code`

**AC-02.1** — Given a subscription not in `PENDING_KYC` (e.g. already `ACTIVE`), when activation is attempted again, then `InvalidSubscriberStateException` is raised, mapped to HTTP 409 / `ALREADY_ACTIVE`.
*Test:* `test_subscriber_api.py::test_activate_an_already_active_subscriber_returns_409`

**AC-01.3 / AC-02.2** — Given two registrations racing for the same mobile number, when both attempt to activate concurrently, then only one reaches `ACTIVE` — the database-level partial unique index is the authoritative guard, not the in-process FSM check alone.
*Test:* `backend/tests/unit/test_activation_service.py::test_two_pending_registrations_for_the_same_mobile_only_one_reaches_active`

## Implementation

- Services: `backend/src/app/service/registration_service.py`, `backend/src/app/service/activation_service.py`
- API: `backend/src/app/api/routers/subscriber_router.py` — `POST /api/subscribers/register`, `POST /api/subscribers/{id}/activate` (both require a subscriber-role bearer token from `POST /api/auth/login`, added once that endpoint existed — see `docs/fix-loops/auth-login-gap.md`)
- UI: `frontend/src/ui/pages/RegisterPage.tsx`, `frontend/src/ui/pages/ActivationStatusPage.tsx`
