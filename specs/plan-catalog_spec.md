# Feature Spec — Plan Catalog (AC-03)

Versioned prepaid/postpaid plan catalog. Published plan versions are immutable; any change creates a new draft version instead.

## Acceptance Criteria

**AC-03.1** — Given an admin creates a new plan, when no prior version exists for that `plan_id`, then the draft is created at `version_number: 1`.
*Test:* `backend/tests/integration/test_plan_api.py::test_create_plan_version_returns_201_with_draft`

**AC-03.2** — Given a draft plan version, when an admin publishes it, then it becomes the version `get_published_version` returns for that `plan_id`.
*Test:* `test_plan_api.py::test_publish_plan_version_returns_200_with_published_true`

**AC-03.3** — Given a published plan version, when anyone attempts to edit its price or terms, then the request is rejected with HTTP 409 / `PLAN_VERSION_IMMUTABLE` — enforced both at the service level (no update function is exposed for a published row) and at the database level (a `BEFORE UPDATE` trigger aborts the statement even if the service layer is bypassed).
*Tests:* `test_plan_api.py::test_put_on_an_already_published_version_returns_409_with_immutability_message`; `backend/tests/unit/test_plan_repository.py`'s direct-SQL bypass tests.

**AC-03.4** — Given a plan with multiple versions, when the admin requests the full catalog, then every version (including superseded ones) is returned in ascending version-number order, none deleted.
*Test:* `test_plan_api.py::test_get_plan_list_returns_full_version_history_including_superseded`

**AC-03.5** — Given a non-admin principal, when they attempt to create, publish, or update a plan version, then the request is rejected with HTTP 403.
*Test:* `test_plan_api.py::test_non_admin_receives_403_for_create_and_list` (+ publish/update variants)

## Implementation

- Service: `backend/src/app/service/plan_catalog_service.py`
- Repository: `backend/src/app/repository/plan_repository.py`
- API: `backend/src/app/api/routers/plan_router.py` — `POST /api/admin/plans`, `POST /api/admin/plans/{id}/publish`, `PUT /api/admin/plans/{id}`, `GET /api/admin/plans`
- UI: `frontend/src/ui/pages/AdminPlanCatalogPage.tsx`
