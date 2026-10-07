"""Unit tests for plan_repository (E3-S1)."""

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.repository.plan_repository import (
    create_plan_version,
    get_plan_version_by_id,
    get_published_version,
    list_all_plan_versions,
    list_current_published_versions,
    list_versions,
    publish_plan_version,
    update_draft_plan_version,
)
from app.types.enums import PlanType
from app.types.plan import PlanVersion

_CREATED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
_PUBLISHED_AT = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)


def _build_draft(plan_id: str, version_number: int, price: str) -> PlanVersion:
    return PlanVersion(
        plan_version_id=f"{plan_id}-v{version_number}",
        plan_id=plan_id,
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        version_number=version_number,
        price=Decimal(price),
        terms={"data_gb": 100, "voice_minutes": "unlimited"},
        published=False,
        created_at=_CREATED_AT,
        published_at=None,
    )


def test_create_plan_version_persists_a_draft(sqlite_connection: sqlite3.Connection) -> None:
    draft = _build_draft("PLAN-5G", 1, "799.00")

    create_plan_version(sqlite_connection, draft)

    versions = list_versions(sqlite_connection, "PLAN-5G")
    assert len(versions) == 1
    assert versions[0] == draft


def test_publish_plan_version_sets_published_flag_and_timestamp(
    sqlite_connection: sqlite3.Connection,
) -> None:
    draft = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, draft)

    publish_plan_version(sqlite_connection, draft.plan_version_id, _PUBLISHED_AT)

    published = get_published_version(sqlite_connection, "PLAN-5G")
    assert published is not None
    assert published.published is True
    assert published.published_at == _PUBLISHED_AT


def test_get_published_version_returns_none_when_no_version_is_published(
    sqlite_connection: sqlite3.Connection,
) -> None:
    create_plan_version(sqlite_connection, _build_draft("PLAN-5G", 1, "799.00"))

    assert get_published_version(sqlite_connection, "PLAN-5G") is None


def test_get_published_version_returns_the_highest_version_number_among_published(
    sqlite_connection: sqlite3.Connection,
) -> None:
    v1 = _build_draft("PLAN-5G", 1, "799.00")
    v2 = _build_draft("PLAN-5G", 2, "899.00")
    create_plan_version(sqlite_connection, v1)
    create_plan_version(sqlite_connection, v2)
    publish_plan_version(sqlite_connection, v1.plan_version_id, _PUBLISHED_AT)
    publish_plan_version(sqlite_connection, v2.plan_version_id, _PUBLISHED_AT)

    published = get_published_version(sqlite_connection, "PLAN-5G")

    assert published is not None
    assert published.version_number == 2
    assert published.price == Decimal("899.00")


def test_list_versions_returns_all_versions_in_ascending_order(
    sqlite_connection: sqlite3.Connection,
) -> None:
    v1 = _build_draft("PLAN-5G", 1, "799.00")
    v2 = _build_draft("PLAN-5G", 2, "899.00")
    v3 = _build_draft("PLAN-5G", 3, "949.00")
    create_plan_version(sqlite_connection, v2)
    create_plan_version(sqlite_connection, v3)
    create_plan_version(sqlite_connection, v1)

    versions = list_versions(sqlite_connection, "PLAN-5G")

    assert [v.version_number for v in versions] == [1, 2, 3]


def test_list_versions_round_trips_decimal_price_and_terms_dict(
    sqlite_connection: sqlite3.Connection,
) -> None:
    draft = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, draft)

    versions = list_versions(sqlite_connection, "PLAN-5G")

    assert versions[0].price == Decimal("799.00")
    assert isinstance(versions[0].price, Decimal)
    assert versions[0].terms == {"data_gb": 100, "voice_minutes": "unlimited"}


def test_direct_update_of_a_published_versions_price_is_rejected(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-4: attempting to mutate a published plan version's price directly fails."""
    draft = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, draft)
    publish_plan_version(sqlite_connection, draft.plan_version_id, _PUBLISHED_AT)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "UPDATE plan_versions SET price = ? WHERE plan_version_id = ?",
            ("1.00", draft.plan_version_id),
        )


def test_direct_delete_of_a_plan_version_is_rejected(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-3: no version is ever deleted, even an unpublished draft."""
    draft = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, draft)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "DELETE FROM plan_versions WHERE plan_version_id = ?", (draft.plan_version_id,)
        )


def test_republishing_an_already_published_version_is_rejected(
    sqlite_connection: sqlite3.Connection,
) -> None:
    draft = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, draft)
    publish_plan_version(sqlite_connection, draft.plan_version_id, _PUBLISHED_AT)

    with pytest.raises(sqlite3.IntegrityError):
        publish_plan_version(sqlite_connection, draft.plan_version_id, datetime.now(UTC))


def test_update_draft_plan_version_changes_price_and_terms(
    sqlite_connection: sqlite3.Connection,
) -> None:
    draft = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, draft)

    update_draft_plan_version(
        sqlite_connection, draft.plan_version_id, Decimal("849.00"), {"data_gb": 150}
    )

    updated = list_versions(sqlite_connection, "PLAN-5G")[0]
    assert updated.price == Decimal("849.00")
    assert updated.terms == {"data_gb": 150}


def test_update_draft_plan_version_on_an_already_published_row_is_rejected(
    sqlite_connection: sqlite3.Connection,
) -> None:
    draft = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, draft)
    publish_plan_version(sqlite_connection, draft.plan_version_id, _PUBLISHED_AT)

    with pytest.raises(sqlite3.IntegrityError):
        update_draft_plan_version(
            sqlite_connection, draft.plan_version_id, Decimal("1.00"), {}
        )


def test_get_plan_version_by_id_finds_the_row_without_needing_plan_id(
    sqlite_connection: sqlite3.Connection,
) -> None:
    draft = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, draft)

    found = get_plan_version_by_id(sqlite_connection, draft.plan_version_id)

    assert found == draft


def test_get_plan_version_by_id_returns_none_when_not_found(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_plan_version_by_id(sqlite_connection, "does-not-exist") is None


def test_list_all_plan_versions_spans_every_plan_id_ordered_by_plan_then_version(
    sqlite_connection: sqlite3.Connection,
) -> None:
    plan_a_v1 = _build_draft("PLAN-4G", 1, "149.00")
    plan_b_v1 = _build_draft("PLAN-5G", 1, "799.00")
    plan_b_v2 = _build_draft("PLAN-5G", 2, "899.00")
    create_plan_version(sqlite_connection, plan_b_v2)
    create_plan_version(sqlite_connection, plan_a_v1)
    create_plan_version(sqlite_connection, plan_b_v1)

    all_versions = list_all_plan_versions(sqlite_connection)

    assert [(v.plan_id, v.version_number) for v in all_versions] == [
        ("PLAN-4G", 1),
        ("PLAN-5G", 1),
        ("PLAN-5G", 2),
    ]


def test_list_all_plan_versions_on_an_empty_database_is_empty(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert list_all_plan_versions(sqlite_connection) == []


def test_list_current_published_versions_excludes_drafts(
    sqlite_connection: sqlite3.Connection,
) -> None:
    published = _build_draft("PLAN-5G", 1, "799.00")
    draft = _build_draft("PLAN-4G", 1, "149.00")
    create_plan_version(sqlite_connection, published)
    create_plan_version(sqlite_connection, draft)
    publish_plan_version(sqlite_connection, published.plan_version_id, _PUBLISHED_AT)

    current = list_current_published_versions(sqlite_connection)

    assert [v.plan_id for v in current] == ["PLAN-5G"]


def test_list_current_published_versions_returns_only_the_highest_published_version_per_plan(
    sqlite_connection: sqlite3.Connection,
) -> None:
    v1 = _build_draft("PLAN-5G", 1, "799.00")
    v2 = _build_draft("PLAN-5G", 2, "899.00")
    create_plan_version(sqlite_connection, v1)
    create_plan_version(sqlite_connection, v2)
    publish_plan_version(sqlite_connection, v1.plan_version_id, _PUBLISHED_AT)
    publish_plan_version(sqlite_connection, v2.plan_version_id, _PUBLISHED_AT)

    current = list_current_published_versions(sqlite_connection)

    assert len(current) == 1
    assert current[0].version_number == 2
    assert current[0].price == Decimal("899.00")


def test_list_current_published_versions_spans_multiple_plan_ids(
    sqlite_connection: sqlite3.Connection,
) -> None:
    plan_a = _build_draft("PLAN-4G", 1, "149.00")
    plan_b = _build_draft("PLAN-5G", 1, "799.00")
    create_plan_version(sqlite_connection, plan_a)
    create_plan_version(sqlite_connection, plan_b)
    publish_plan_version(sqlite_connection, plan_a.plan_version_id, _PUBLISHED_AT)
    publish_plan_version(sqlite_connection, plan_b.plan_version_id, _PUBLISHED_AT)

    current = list_current_published_versions(sqlite_connection)

    assert {v.plan_id for v in current} == {"PLAN-4G", "PLAN-5G"}


def test_list_current_published_versions_on_an_empty_database_is_empty(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert list_current_published_versions(sqlite_connection) == []
