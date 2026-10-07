"""Unit tests for the plan catalog service (E3-S2)."""

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.repository.plan_repository import get_published_version, list_versions
from app.service.plan_catalog_service import (
    create_draft_plan_version,
    list_published_catalog,
    publish_plan_version,
    update_draft_plan_version,
)
from app.types.auth import Principal
from app.types.enums import PlanType, Role
from app.types.exceptions import AuthorizationError, PlanVersionImmutableError

_CREATED_AT = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
_PUBLISHED_AT = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)

_ADMIN = Principal(user_id="admin-1", role=Role.ADMIN, subscriber_id=None)
_SUBSCRIBER = Principal(
    user_id="subscriber-1", role=Role.SUBSCRIBER, subscriber_id="sub-1"
)
_CSR = Principal(user_id="csr-1", role=Role.CSR, subscriber_id=None)


def test_create_draft_plan_version_starts_at_version_number_one(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-1: a brand-new plan starts an unpublished draft at version 1."""
    draft = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_CREATED_AT,
    )

    assert draft.version_number == 1
    assert draft.published is False


def test_publishing_a_draft_makes_it_the_version_returned_by_get_published_version(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2."""
    draft = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_CREATED_AT,
    )

    published = publish_plan_version(
        sqlite_connection, _ADMIN, "PLAN-5G", draft.plan_version_id, _PUBLISHED_AT
    )

    assert published.published is True
    assert get_published_version(sqlite_connection, "PLAN-5G") == published


def test_editing_a_published_versions_price_raises_plan_version_immutable_error(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-3."""
    draft = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_CREATED_AT,
    )
    publish_plan_version(sqlite_connection, _ADMIN, "PLAN-5G", draft.plan_version_id, _PUBLISHED_AT)

    with pytest.raises(PlanVersionImmutableError):
        update_draft_plan_version(
            sqlite_connection,
            _ADMIN,
            "PLAN-5G",
            draft.plan_version_id,
            price=Decimal("1.00"),
            terms={},
        )

    unchanged = get_published_version(sqlite_connection, "PLAN-5G")
    assert unchanged is not None
    assert unchanged.price == Decimal("799.00")


def test_updating_an_unpublished_draft_succeeds(sqlite_connection: sqlite3.Connection) -> None:
    draft = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_CREATED_AT,
    )

    updated = update_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        "PLAN-5G",
        draft.plan_version_id,
        price=Decimal("849.00"),
        terms={"data_gb": 150},
    )

    assert updated.price == Decimal("849.00")
    assert updated.terms == {"data_gb": 150}


def test_requesting_a_change_to_a_published_plan_creates_a_new_incremented_draft(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-4: the prior published version is left unchanged and retrievable."""
    v1 = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_CREATED_AT,
    )
    publish_plan_version(sqlite_connection, _ADMIN, "PLAN-5G", v1.plan_version_id, _PUBLISHED_AT)

    v2 = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("899.00"),
        terms={"data_gb": 120},
        created_at=_PUBLISHED_AT,
    )

    assert v2.version_number == 2
    assert v2.published is False

    versions = list_versions(sqlite_connection, "PLAN-5G")
    assert len(versions) == 2
    v1_reloaded = next(v for v in versions if v.plan_version_id == v1.plan_version_id)
    assert v1_reloaded.published is True
    assert v1_reloaded.price == Decimal("799.00")  # unchanged
    assert get_published_version(sqlite_connection, "PLAN-5G") == v1_reloaded


@pytest.mark.parametrize("non_admin", [_SUBSCRIBER, _CSR])
def test_non_admin_cannot_create_a_draft_plan_version(
    sqlite_connection: sqlite3.Connection, non_admin: Principal
) -> None:
    """AC-5."""
    with pytest.raises(AuthorizationError):
        create_draft_plan_version(
            sqlite_connection,
            non_admin,
            plan_id="PLAN-5G",
            plan_name="Unlimited 5G Postpaid",
            plan_type=PlanType.POSTPAID,
            price=Decimal("799.00"),
            terms={"data_gb": 100},
            created_at=_CREATED_AT,
        )

    assert list_versions(sqlite_connection, "PLAN-5G") == []


def test_non_admin_cannot_publish_a_plan_version(sqlite_connection: sqlite3.Connection) -> None:
    """AC-5."""
    draft = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_CREATED_AT,
    )

    with pytest.raises(AuthorizationError):
        publish_plan_version(
            sqlite_connection, _CSR, "PLAN-5G", draft.plan_version_id, _PUBLISHED_AT
        )

    assert get_published_version(sqlite_connection, "PLAN-5G") is None


def test_non_admin_cannot_update_a_draft_plan_version(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-5."""
    draft = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_CREATED_AT,
    )

    with pytest.raises(AuthorizationError):
        update_draft_plan_version(
            sqlite_connection,
            _SUBSCRIBER,
            "PLAN-5G",
            draft.plan_version_id,
            price=Decimal("1.00"),
            terms={},
        )


def test_update_draft_plan_version_raises_for_an_unknown_plan_version_id(
    sqlite_connection: sqlite3.Connection,
) -> None:
    with pytest.raises(ValueError, match="not found"):
        update_draft_plan_version(
            sqlite_connection,
            _ADMIN,
            "PLAN-5G",
            "does-not-exist",
            price=Decimal("1.00"),
            terms={},
        )


def test_list_published_catalog_excludes_drafts_and_is_open_to_any_role(
    sqlite_connection: sqlite3.Connection,
) -> None:
    draft = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_CREATED_AT,
    )
    publish_plan_version(sqlite_connection, _ADMIN, "PLAN-5G", draft.plan_version_id, _PUBLISHED_AT)
    create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-4G",
        plan_name="4G Basic",
        plan_type=PlanType.PREPAID,
        price=Decimal("149.00"),
        terms={"data_gb": 10},
        created_at=_CREATED_AT,
    )

    catalog_for_subscriber = list_published_catalog(sqlite_connection)
    catalog_for_csr = list_published_catalog(sqlite_connection)

    assert [v.plan_id for v in catalog_for_subscriber] == ["PLAN-5G"]
    assert catalog_for_csr == catalog_for_subscriber
