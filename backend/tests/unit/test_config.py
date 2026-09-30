"""Unit tests for the Config layer: settings, stub flags, and DB connection.

(E1-S2 AC-1, AC-2, AC-4, AC-5)
"""

import sqlite3
from pathlib import Path

import pytest

from app.config.db import create_connection
from app.config.settings import Settings, get_settings
from app.config.stub_flags import (
    DEFAULT_DEALER_FAIL_CODE,
    DEFAULT_KYC_STUB_VERIFIED,
    DEFAULT_MNP_STUB_SUCCESS,
)


def test_settings_falls_back_to_documented_defaults_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_var in (
        "DB_PATH",
        "KYC_STUB_VERIFIED",
        "MNP_STUB_SUCCESS",
        "DEALER_FAIL_CODE",
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "JWT_EXPIRY_MINUTES",
        "MIN_TENURE_DAYS",
    ):
        monkeypatch.delenv(env_var, raising=False)

    settings = Settings(_env_file=None)

    assert settings.db_path == "./data/telcolane.db"
    assert settings.kyc_stub_verified == DEFAULT_KYC_STUB_VERIFIED
    assert settings.mnp_stub_success == DEFAULT_MNP_STUB_SUCCESS
    assert settings.dealer_fail_code == DEFAULT_DEALER_FAIL_CODE
    assert settings.jwt_secret_key == "dev-only-insecure-secret-change-in-production"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expiry_minutes == 60
    assert settings.min_tenure_days == 90


def test_settings_reads_overrides_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_PATH", "/var/telcolane/prod.db")
    monkeypatch.setenv("KYC_STUB_VERIFIED", "false")
    monkeypatch.setenv("MNP_STUB_SUCCESS", "false")
    monkeypatch.setenv("DEALER_FAIL_CODE", "DEALER-FAIL")
    monkeypatch.setenv("JWT_SECRET_KEY", "integration-test-secret-that-is-at-least-32-bytes-long")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_EXPIRY_MINUTES", "15")
    monkeypatch.setenv("MIN_TENURE_DAYS", "30")

    settings = Settings(_env_file=None)

    assert settings.db_path == "/var/telcolane/prod.db"
    assert settings.kyc_stub_verified is False
    assert settings.mnp_stub_success is False
    assert settings.dealer_fail_code == "DEALER-FAIL"
    assert settings.jwt_secret_key == "integration-test-secret-that-is-at-least-32-bytes-long"
    assert settings.jwt_expiry_minutes == 15
    assert settings.min_tenure_days == 30


def test_get_settings_returns_a_settings_instance() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_stub_flag_constants_are_exact_string_and_boolean_values_for_activation_service() -> (
    None
):
    assert DEFAULT_DEALER_FAIL_CODE == "DEALER-FAIL"
    assert isinstance(DEFAULT_DEALER_FAIL_CODE, str)
    assert DEFAULT_KYC_STUB_VERIFIED is True
    assert isinstance(DEFAULT_KYC_STUB_VERIFIED, bool)
    assert DEFAULT_MNP_STUB_SUCCESS is True
    assert isinstance(DEFAULT_MNP_STUB_SUCCESS, bool)


def test_create_connection_applies_wal_journal_mode(tmp_path: Path) -> None:
    db_path = str(tmp_path / "telcolane_test.db")

    connection = create_connection(db_path)

    try:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal_mode == "wal"
    finally:
        connection.close()


def test_create_connection_returns_a_working_sqlite_connection(tmp_path: Path) -> None:
    db_path = str(tmp_path / "telcolane_test2.db")

    connection = create_connection(db_path)

    try:
        assert isinstance(connection, sqlite3.Connection)
        connection.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO probe (id) VALUES (1)")
        row = connection.execute("SELECT id FROM probe").fetchone()
        assert row[0] == 1
    finally:
        connection.close()
