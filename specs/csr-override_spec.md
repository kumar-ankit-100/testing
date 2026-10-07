# Feature Spec — CSR Overrides (AC-09) and Termination

CSR override of a rejected activation or plan-change, and CSR/admin-only subscription termination.

## Acceptance Criteria

**AC-09.1** — Given a rejected activation (e.g. `DEALER_INVALID`), when a CSR overrides it with a reason code, then the activation is forced through — re-invoking the *same* `activate_subscriber` service function with only the one failed rule suppressed, not a separate bypass code path — and the subscription reaches `ACTIVE`.
*Test:* `backend/tests/integration/test_csr_api.py::test_csr_override_activation_with_dealer_fail_returns_200_active`

**AC-09.2** — Given a rejected plan change (e.g. `MIN_TENURE_NOT_MET`), when a CSR overrides it, then the change commits via the same `commit_plan_change` path used by the normal flow.
*Test:* `test_csr_api.py::test_csr_override_plan_change_commits_despite_min_tenure`

**AC-09.3** — Given an override attempt with no reason code, when submitted, then it is rejected (422) before any state change or audit record is written.
*Test:* `test_csr_api.py::test_csr_override_activation_without_reason_code_returns_422`

**AC-09.4** — Given a non-CSR principal (e.g. admin), when they attempt an override, then it is rejected with HTTP 403.
*Test:* `test_csr_api.py::test_non_csr_cannot_override_activation`

**AC-09.5** — Given any override attempt, succeeding or failing, when it reaches the persistence step, then an append-only `CSROverride` row is written with a non-null actor, reason code, and timestamp.
*Test:* `backend/tests/unit/test_csr_override_service.py` (audit-record assertions)

### Termination (CSR/admin-only, same audit discipline)

**Termination.1** — Given an ACTIVE or SUSPENDED subscription, when a CSR or admin terminates it with a reason code, then it transitions to `TERMINATED` and an append-only `StateTransition` is written (reusing the existing audit table rather than a new one, since termination is a legitimate transition, not an override of a rejection).
*Tests:* `backend/tests/integration/test_lifecycle_api.py::test_csr_can_terminate_an_active_subscription`, `test_admin_can_terminate_a_suspended_subscription`

**Termination.2** — Given a subscriber's own token, when they attempt to terminate their own subscription, then it is rejected with 403 — termination is CSR/admin-only regardless of ownership.
*Test:* `test_lifecycle_api.py::test_subscriber_cannot_terminate_their_own_subscription`

## Implementation

- Services: `backend/src/app/service/csr_override_service.py`, `backend/src/app/service/termination_service.py`
- API: `backend/src/app/api/routers/csr_router.py` — `POST /api/csr/overrides/{activation,plan-change}/{id}`; `backend/src/app/api/routers/lifecycle_router.py` — `POST /api/subscriptions/{id}/terminate`
- UI: `frontend/src/ui/pages/CsrExceptionQueuePage.tsx` — a direct-entry tool (enter the subscriber/subscription ID), not a queue view, since no repository query exists yet to list pending exceptions across subscribers (only per-subscription override history). A future story adding that query would replace the manual entry with a real selectable list.
