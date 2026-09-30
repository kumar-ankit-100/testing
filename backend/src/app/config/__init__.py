"""Config layer — environment settings and deterministic stub flags.

Imports Types only.
"""

from app.config.db import create_connection
from app.config.settings import Settings, get_settings
from app.config.stub_flags import (
    DEFAULT_DEALER_FAIL_CODE,
    DEFAULT_KYC_STUB_VERIFIED,
    DEFAULT_MNP_STUB_SUCCESS,
)

__all__ = [
    "DEFAULT_DEALER_FAIL_CODE",
    "DEFAULT_KYC_STUB_VERIFIED",
    "DEFAULT_MNP_STUB_SUCCESS",
    "Settings",
    "create_connection",
    "get_settings",
]
