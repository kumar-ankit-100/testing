"""Unit tests for the admin reporting service (E7-S2)."""

import sqlite3
from decimal import Decimal

import pytest

from app.service.reporting_service import _as_percentages, get_admin_dashboard
from app.types.auth import Principal
from app.types.enums import Role
from app.types.exceptions import AuthorizationError


def _admin_principal() -> Principal:
    return Principal(user_id="admin-001", role=Role.ADMIN, subscriber_id=None)


def _csr_principal() -> Principal:
    return Principal(user_id="csr-001", role=Role.CSR, subscriber_id=None)


def test_dashboard_on_an_empty_database_returns_a_well_formed_empty_funnel(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-1: zero-activations period returns a well-formed empty funnel,
    no exception raised."""
    dashboard = get_admin_dashboard(sqlite_connection, _admin_principal())

    assert dashboard["activation_funnel"] == {
        "registered": 0,
        "kyc_passed": 0,
        "dealer_passed": 0,
        "mnp_passed": 0,
        "activated": 0,
    }
    assert dashboard["plan_mix"] == {}
    assert dashboard["churn"] == {}
    assert dashboard["arpu_trend"] == {}


def test_plan_mix_percentages_sum_to_100_within_tolerance(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2."""
    sqlite_connection.executescript(
        """
        INSERT INTO subscribers (subscriber_id, mobile_number, identity_proof_ref, created_at)
        VALUES
          ('s1', '9000000001', 'id1', '2026-01-01T00:00:00+00:00'),
          ('s2', '9000000002', 'id2', '2026-01-01T00:00:00+00:00'),
          ('s3', '9000000003', 'id3', '2026-01-01T00:00:00+00:00');
        INSERT INTO subscriptions (
            subscription_id, subscriber_id, mobile_number, plan_type, state,
            current_plan_version_id, dealer_code, created_at, activated_at, updated_at
        ) VALUES
          ('sub1', 's1', '9000000001', 'PREPAID', 'ACTIVE', NULL, NULL,
           '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'),
          ('sub2', 's2', '9000000002', 'POSTPAID', 'ACTIVE', NULL, NULL,
           '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'),
          ('sub3', 's3', '9000000003', 'POSTPAID', 'ACTIVE', NULL, NULL,
           '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00');
        """
    )
    sqlite_connection.commit()

    dashboard = get_admin_dashboard(sqlite_connection, _admin_principal())
    percentages = dashboard["plan_mix_percentages"]
    total = sum(percentages.values())
    assert abs(float(total) - 100.0) <= 0.1


def test_as_percentages_corrects_a_rounding_remainder_onto_the_largest_bucket() -> None:
    """AC-2: three equal buckets (1/3 each) round to 33.33 independently,
    summing to 99.99 — the 0.01 remainder is given to the largest bucket
    so the total is always exactly 100.00."""
    percentages = _as_percentages({"A": 1, "B": 1, "C": 1})

    assert sum(percentages.values()) == Decimal("100.00")
    assert percentages["A"] == Decimal("33.34")
    assert percentages["B"] == Decimal("33.33")
    assert percentages["C"] == Decimal("33.33")


def test_as_percentages_on_an_empty_dict_returns_empty() -> None:
    assert _as_percentages({}) == {}


def test_arpu_trend_metadata_is_labeled_as_stubbed(sqlite_connection: sqlite3.Connection) -> None:
    """AC-3."""
    dashboard = get_admin_dashboard(sqlite_connection, _admin_principal())

    assert dashboard["metadata"]["arpu_trend_is_stubbed"] is True


def test_dashboard_denies_a_non_admin_principal(sqlite_connection: sqlite3.Connection) -> None:
    """AC-4: enforced at the service level independent of the API layer."""
    with pytest.raises(AuthorizationError):
        get_admin_dashboard(sqlite_connection, _csr_principal())
