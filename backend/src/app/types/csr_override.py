"""CSROverride domain type.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass
from datetime import datetime

from app.types.enums import OverriddenAction


@dataclass(frozen=True)
class CSROverride:
    """An append-only audit row for a CSR re-running a rejected action."""

    override_id: str
    subscription_id: str
    actor: str
    reason_code: str
    overridden_action: OverriddenAction
    original_rejection_reason: str
    created_at: datetime
