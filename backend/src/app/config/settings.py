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
    # JWT settings (added E1-S4): jwt_secret_key's default is an explicitly
    # dev-only placeholder, not a real credential — override via the
    # JWT_SECRET_KEY env var for any non-local environment.
    jwt_secret_key: str = "dev-only-insecure-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60


def get_settings() -> Settings:
    """Build a fresh Settings instance from the current environment.

    Deliberately uncached: services under test must be able to construct
    Settings with per-test overrides without leaking cached state across
    tests (see SKILL.md ".env leaking into tests" gotcha).
    """
    return Settings()
