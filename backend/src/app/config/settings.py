"""Typed application settings for TelcoLane.

Config layer — imports Types only.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.stub_flags import (
    DEFAULT_DEALER_FAIL_CODE,
    DEFAULT_KYC_STUB_VERIFIED,
    DEFAULT_MNP_STUB_SUCCESS,
)


class Settings(BaseSettings):
    """Environment-backed settings with documented defaults.

    Field names map to environment variables of the same name, uppercased
    (e.g. `db_path` <- `DB_PATH`), per pydantic-settings' default behavior.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = "./data/telcolane.db"
    kyc_stub_verified: bool = DEFAULT_KYC_STUB_VERIFIED
    mnp_stub_success: bool = DEFAULT_MNP_STUB_SUCCESS
    dealer_fail_code: str = DEFAULT_DEALER_FAIL_CODE


def get_settings() -> Settings:
    """Build a fresh Settings instance from the current environment.

    Deliberately uncached: services under test must be able to construct
    Settings with per-test overrides without leaking cached state across
    tests (see SKILL.md ".env leaking into tests" gotcha).
    """
    return Settings()
