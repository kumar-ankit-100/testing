# TelcoLane — Component Map

Maps every story to the files created or modified to implement it, per `folder-structure.md`. Paths are relative to `backend/` or `frontend/`.

| Story ID | Title | Layer | Files Created / Modified |
|---|---|---|---|
| E1-S1 | Define core domain types and FSM contracts | Types | `src/app/types/enums.py`, `src/app/types/fsm.py`, `src/app/types/exceptions.py`, `src/app/types/subscriber.py`, `src/app/types/subscription.py`, `src/app/types/plan.py`, `src/app/types/billing.py`, `src/app/types/state_transition.py`, `src/app/types/port_out.py`, `src/app/types/csr_override.py`, `src/app/types/dealer.py`; `tests/unit/test_types.py`, `tests/unit/test_fsm.py` |
| E1-S2 | Application configuration and stub integration flags | Config | `src/app/config/settings.py`, `src/app/config/stub_flags.py`, `src/app/config/db.py`; `tests/unit/test_config.py` |
| E1-S3 | Structured JSON logging with PII masking | Service | `src/app/lib/pii_mask.py`, `src/app/service/logging_service.py`; `tests/unit/test_logging_service.py` |
| E1-S4 | Role-based auth and controller-level authorization | API | `src/app/types/auth.py`, `src/app/repository/user_repository.py`, `src/app/service/auth_service.py`, `src/app/api/deps.py`; `tests/integration/test_auth.py` |
| E1-S5 | Health check endpoint | API | `src/app/api/routers/health_router.py`, `src/app/api/main.py`; `tests/integration/test_health.py` |
| E2-S1 | Subscriber repository and seeded dealer master | Repository | `src/app/repository/subscriber_repository.py`, `src/app/repository/dealer_repository.py`, `src/app/repository/schema.sql`; `tests/unit/test_subscriber_repository.py`, `tests/unit/test_dealer_repository.py` |
| E2-S2 | Subscriber self-registration service | Service | `src/app/service/registration_service.py`; `tests/unit/test_registration_service.py` |
| E2-S3 | Rule-based activation engine (KYC, dealer, MNP) | Service | `src/app/service/activation_service.py`; `tests/unit/test_activation_service.py` |
| E2-S4 | Registration and activation API endpoints | API | `src/app/api/routers/subscriber_router.py`, `src/app/api/schemas/subscriber_schemas.py`, `src/app/api/main.py` (mount router); `tests/integration/test_subscriber_api.py` |
| E2-S5 | Subscriber self-registration and activation status UI | UI | `src/types/domain.ts`, `src/types/api.ts`, `src/api/subscriberApi.ts`, `src/service/useRegistration.ts`, `src/service/useActivationStatus.ts`, `src/ui/pages/RegisterPage.tsx`, `src/ui/pages/ActivationStatusPage.tsx`; `e2e/registration.spec.ts` |
| E3-S1 | Plan catalog repository with version history | Repository | `src/app/repository/plan_repository.py` (schema additions in `schema.sql`); `tests/unit/test_plan_repository.py` |
| E3-S2 | Plan catalog service — versioning and immutability | Service | `src/app/service/plan_catalog_service.py`; `tests/unit/test_plan_catalog_service.py` |
| E3-S3 | Plan catalog admin API endpoints | API | `src/app/api/routers/plan_router.py`, `src/app/api/schemas/plan_schemas.py`; `tests/integration/test_plan_api.py` |
| E3-S4 | Admin plan catalog management UI | UI | `src/api/planApi.ts`, `src/service/usePlanCatalog.ts`, `src/ui/pages/AdminPlanCatalogPage.tsx`, `src/ui/components/StateBadge.tsx`; `e2e/admin-plan-catalog.spec.ts` |
| E4-S1 | Billing record repository (append-only) | Repository | `src/app/repository/billing_repository.py` (schema + trigger in `schema.sql`); `tests/unit/test_billing_repository.py` |
| E4-S2 | Pro-rata billing calculation service | Service | `src/app/service/billing_calculation_service.py`; `tests/unit/test_billing_calculation_service.py` |
| E4-S3 | Plan change service — upgrade/downgrade with minimum-tenure rule | Service | `src/app/service/plan_change_service.py`; `tests/unit/test_plan_change_service.py` |
| E4-S4 | Plan change API endpoints | API | `src/app/api/routers/plan_change_router.py`, `src/app/api/schemas/plan_change_schemas.py`; `tests/integration/test_plan_change_api.py` |
| E4-S5 | Subscriber plan upgrade/downgrade UI | UI | `src/api/planChangeApi.ts`, `src/service/usePlanChange.ts`, `src/ui/pages/PlanChangePage.tsx`; `e2e/plan-change.spec.ts` |
| E5-S1 | State transition and port-out event repositories (append-only) | Repository | `src/app/repository/state_transition_repository.py`, `src/app/repository/port_out_repository.py` (schema + triggers in `schema.sql`); `tests/unit/test_state_transition_repository.py`, `tests/unit/test_port_out_repository.py` |
| E5-S2 | Suspend/resume service | Service | `src/app/service/suspend_resume_service.py`; `tests/unit/test_suspend_resume_service.py` |
| E5-S3 | Port-out request service with 7-day cooling period | Service | `src/app/service/port_out_service.py`; `tests/unit/test_port_out_service.py` |
| E5-S4 | Suspend/resume and port-out API endpoints | API | `src/app/api/routers/lifecycle_router.py`, `src/app/api/schemas/lifecycle_schemas.py`; `tests/integration/test_lifecycle_api.py` |
| E5-S5 | Subscriber suspend/resume/port-out UI | UI | `src/api/lifecycleApi.ts`, `src/service/useLifecycle.ts`, `src/ui/pages/LifecyclePage.tsx`, `src/ui/components/CountdownTimer.tsx`; `e2e/lifecycle.spec.ts` |
| E6-S1 | CSR override repository (append-only, audited) | Repository | `src/app/repository/csr_override_repository.py` (schema in `schema.sql`); `tests/unit/test_csr_override_repository.py` |
| E6-S2 | CSR override service — override rejected activation/plan-change | Service | `src/app/service/csr_override_service.py`; `tests/unit/test_csr_override_service.py` |
| E6-S3 | CSR exception queue API endpoints | API | `src/app/api/routers/csr_router.py`, `src/app/api/schemas/csr_schemas.py`; `tests/integration/test_csr_api.py` |
| E6-S4 | CSR exception queue desktop UI | UI | `src/api/csrApi.ts`, `src/service/useCsrExceptions.ts`, `src/ui/pages/CsrExceptionQueuePage.tsx`; `e2e/csr-queue.spec.ts` |
| E6-S5 | CSR/Admin subscription termination service | Service | `src/app/service/termination_service.py`; `tests/unit/test_termination_service.py` |
| E6-S6 | Subscription termination API endpoint | API | `src/app/api/routers/lifecycle_router.py` (extended), `src/app/api/schemas/lifecycle_schemas.py` (extended); `tests/integration/test_lifecycle_api.py` (extended) |
| E7-S1 | Reporting query repository | Repository | `src/app/repository/reporting_repository.py`; `tests/unit/test_reporting_repository.py` |
| E7-S2 | Admin reporting service | Service | `src/app/service/reporting_service.py`; `tests/unit/test_reporting_service.py` |
| E7-S3 | Admin reporting API endpoints | API | `src/app/api/routers/admin_reports_router.py`, `src/app/api/schemas/report_schemas.py`; `tests/integration/test_admin_reports_api.py` |
| E7-S4 | Admin reporting dashboard UI | UI | `src/api/reportsApi.ts`, `src/service/useReports.ts`, `src/ui/pages/AdminReportsDashboardPage.tsx`; `e2e/admin-reports.spec.ts` |

## Cross-cutting files touched by multiple stories

| File | Touched by |
|---|---|
| `backend/src/app/repository/schema.sql` | E2-S1, E3-S1, E4-S1, E5-S1, E6-S1 (each adds its own tables/triggers/seed data) |
| `backend/src/app/api/main.py` | E1-S5, E2-S4 (and every subsequent API story mounts its router here) |
| `backend/src/app/api/error_handlers.py` | E1-S4 (initial 401/403 mapping), then extended by E2-S4, E3-S3, E4-S4, E5-S4, E6-S3 as new reason codes are introduced |
| `backend/src/app/api/routers/lifecycle_router.py` | E5-S4 (suspend/resume/port-out), extended by E6-S6 (terminate) |
| `backend/src/app/api/schemas/lifecycle_schemas.py` | E5-S4, extended by E6-S6 |
| `frontend/src/types/api.ts` | Extended by every UI story (E2-S5, E3-S4, E4-S5, E5-S5, E6-S4, E7-S4) as each adds its endpoints' DTOs |
