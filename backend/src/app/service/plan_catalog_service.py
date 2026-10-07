"""Plan catalog service — versioning and immutability (E3-S2).

Service layer — imports Types, Config, Repository. All three mutating
operations (create, update-draft, publish) are admin-only, checked here
independently of the API layer (system-design.md 5.4's documented
exception pattern, also used by E7-S2's reporting service).
"""

import sqlite3
import uuid
from datetime import datetime
from decimal import Decimal

from app.repository import plan_repository
from app.types.auth import Principal
from app.types.enums import PlanType, Role
from app.types.exceptions import AuthorizationError, PlanVersionImmutableError
from app.types.plan import PlanVersion


def create_draft_plan_version(
    connection: sqlite3.Connection,
    principal: Principal,
    plan_id: str,
    plan_name: str,
    plan_type: PlanType,
    price: Decimal,
    terms: dict[str, object],
    created_at: datetime,
) -> PlanVersion:
    """Create a new draft version: version 1 for a brand-new plan_id, or
    the next version number if plan_id already has versions (AC-1, AC-4).
    """
    _require_admin(principal)

    existing_versions = plan_repository.list_versions(connection, plan_id)
    next_version_number = (
        max(version.version_number for version in existing_versions) + 1
        if existing_versions
        else 1
    )

    draft = PlanVersion(
        plan_version_id=str(uuid.uuid4()),
        plan_id=plan_id,
        plan_name=plan_name,
        plan_type=plan_type,
        version_number=next_version_number,
        price=price,
        terms=terms,
        published=False,
        created_at=created_at,
        published_at=None,
    )
    plan_repository.create_plan_version(connection, draft)
    return draft


def update_draft_plan_version(
    connection: sqlite3.Connection,
    principal: Principal,
    plan_id: str,
    plan_version_id: str,
    price: Decimal,
    terms: dict[str, object],
) -> PlanVersion:
    """Update a draft's price/terms; raises PlanVersionImmutableError if
    plan_version_id is already published (AC-3), before any DB write.
    """
    _require_admin(principal)
    target = _find_version(connection, plan_id, plan_version_id)
    if target.published:
        raise PlanVersionImmutableError(plan_version_id)

    plan_repository.update_draft_plan_version(connection, plan_version_id, price, terms)
    return _find_version(connection, plan_id, plan_version_id)


def publish_plan_version(
    connection: sqlite3.Connection,
    principal: Principal,
    plan_id: str,
    plan_version_id: str,
    published_at: datetime,
) -> PlanVersion:
    """Publish a draft; it becomes the version get_published_version
    returns for plan_id (AC-2).
    """
    _require_admin(principal)
    plan_repository.publish_plan_version(connection, plan_version_id, published_at)
    return _find_version(connection, plan_id, plan_version_id)


def list_published_catalog(connection: sqlite3.Connection) -> list[PlanVersion]:
    """Return the current published version of every plan_id — deliberately
    open to any authenticated role (no _require_admin call), since
    subscribers need this to browse plans at registration and when
    choosing a plan-change target.
    """
    return plan_repository.list_current_published_versions(connection)


def _require_admin(principal: Principal) -> None:
    if principal.role != Role.ADMIN:
        raise AuthorizationError(
            f"Role {principal.role.value} may not create or publish plan versions"
        )


def _find_version(
    connection: sqlite3.Connection, plan_id: str, plan_version_id: str
) -> PlanVersion:
    for version in plan_repository.list_versions(connection, plan_id):
        if version.plan_version_id == plan_version_id:
            return version
    raise ValueError(f"Plan version {plan_version_id!r} not found for plan {plan_id!r}")
