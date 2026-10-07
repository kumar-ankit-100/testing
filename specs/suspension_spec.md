# Feature Spec — Suspend / Resume (AC-06, AC-02)

Subscriber-initiated suspension and reactivation.

## Acceptance Criteria

**AC-06.1** — Given an ACTIVE subscription, when suspend is requested, then it transitions to `SUSPENDED` and an append-only `StateTransition` is written.
*Test:* `backend/tests/integration/test_lifecycle_api.py::test_suspend_an_active_subscription_returns_200_suspended`

**AC-06.2** — Given a SUSPENDED subscription, when resume is requested, then it transitions back to `ACTIVE` (consumption, stubbed, resumes).
*Test:* `test_lifecycle_api.py::test_resume_a_suspended_subscription_returns_200_active`

**AC-02.3** — Given a subscription not currently in the required source state (e.g. suspending a `PENDING_KYC` subscription, or resuming an `ACTIVE` one), when the action is attempted, then `InvalidSubscriberStateException` is raised — checked explicitly against the *current* state, not inferred from the generic FSM edge table alone, because `ACTIVE` has more than one valid incoming edge (activation, port-out cancel, resume) that the FSM can't disambiguate by itself.
*Test:* `backend/tests/unit/test_suspend_resume_service.py::test_resuming_a_non_suspended_subscription_raises_invalid_state_exception` — this exact ambiguity was a real bug caught during development (see `backend/src/app/service/suspend_resume_service.py`'s module docstring) and fixed with an explicit `expected_from_state` check ahead of the generic FSM call.

**NFR-04** — Given a subscriber's token, when they suspend/resume a subscription that isn't theirs, it's rejected with 403; staff bypass this check.
*Tests:* `test_lifecycle_api.py::test_subscriber_cannot_suspend_another_subscribers_subscription`, `test_staff_can_suspend_without_an_ownership_check`

## Implementation

- Service: `backend/src/app/service/suspend_resume_service.py`
- API: `backend/src/app/api/routers/lifecycle_router.py` — `POST /api/subscriptions/{id}/{suspend,resume}`
- UI: `frontend/src/ui/pages/ActivationStatusPage.tsx`'s subscription-management panel
