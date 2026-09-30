"""Unit tests for dealer_repository and DealerMaster seed data (E2-S1)."""

import sqlite3

from app.config.stub_flags import DEFAULT_DEALER_FAIL_CODE
from app.repository.dealer_repository import get_dealer_by_code


def test_dealer_fail_sentinel_is_seeded_on_schema_apply(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-3: the DEALER-FAIL sentinel is present after schema.sql runs."""
    dealer = get_dealer_by_code(sqlite_connection, DEFAULT_DEALER_FAIL_CODE)

    assert dealer is not None
    assert dealer.dealer_code == "DEALER-FAIL"


def test_at_least_five_valid_dealer_codes_are_seeded(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-3: at least 5 valid (non-sentinel) dealer codes are seeded."""
    row = sqlite_connection.execute(
        "SELECT COUNT(*) FROM dealer_master WHERE dealer_code != ?",
        (DEFAULT_DEALER_FAIL_CODE,),
    ).fetchone()

    assert row[0] >= 5


def test_seeded_valid_dealers_are_active(sqlite_connection: sqlite3.Connection) -> None:
    row = sqlite_connection.execute(
        "SELECT COUNT(*) FROM dealer_master WHERE dealer_code != ? AND active = 0",
        (DEFAULT_DEALER_FAIL_CODE,),
    ).fetchone()

    assert row[0] == 0


def test_get_dealer_by_code_returns_none_for_an_unknown_code(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_dealer_by_code(sqlite_connection, "DLR-UNKNOWN-999") is None


def test_get_dealer_by_code_returns_typed_dealer_master(
    sqlite_connection: sqlite3.Connection,
) -> None:
    dealer = get_dealer_by_code(sqlite_connection, "DLR-BLR-001")

    assert dealer is not None
    assert dealer.dealer_name
    assert isinstance(dealer.active, bool)
