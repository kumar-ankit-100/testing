# Feature Spec — Port-Out Workflow (AC-07, AC-02)

7-day cooling-period state machine for number port-out.

## Acceptance Criteria

**AC-07.1** — Given an ACTIVE subscription, when port-out is requested, then it transitions to `PORT_OUT_REQUESTED` and an append-only `PortOutEvent` is created with `cooling_period_end_at` computed and stored as exactly `requested_at + 7 days` at request time (not recomputed on every read, so a later config change can't retroactively shift an in-flight window).
*Test:* `backend/tests/integration/test_lifecycle_api.py::test_port_out_request_returns_200_with_cooling_period_end_date`

**AC-07.2** — Given a `PORT_OUT_REQUESTED` subscription within its cooling period, when cancel is requested, then it returns to `ACTIVE` and the event closes as `CANCELLED_WITHIN_WINDOW`.
*Test:* `test_lifecycle_api.py::test_cancel_port_out_within_window_returns_200_active`

**AC-07.3** — Given a `PORT_OUT_REQUESTED` subscription whose cooling period has elapsed, when finalize is requested, then it transitions to `PORTED_OUT` (terminal) and the event closes as `FINALIZED`.
*Test:* `test_lifecycle_api.py::test_finalize_port_out_after_window_elapsed_returns_200_ported_out` — seeds a port-out event 8 days in the past directly via the repository, since the live API always uses "now" for `requested_at` and there's no way to fast-forward real time through the HTTP layer.

**AC-07.4** — Given a `PORT_OUT_REQUESTED` subscription whose cooling period has *not* elapsed, when finalize is requested, then it is rejected with HTTP 422 / `COOLING_PERIOD_NOT_ELAPSED`.
*Test:* `test_lifecycle_api.py::test_finalize_port_out_before_window_elapses_returns_422`

## Implementation

- Service: `backend/src/app/service/port_out_service.py`
- Repository: `backend/src/app/repository/port_out_repository.py`
- API: `backend/src/app/api/routers/lifecycle_router.py` — `POST /api/subscriptions/{id}/port-out/{request,cancel,finalize}`
- UI: `frontend/src/ui/pages/ActivationStatusPage.tsx`'s subscription-management panel
