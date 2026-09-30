"""Subscriber domain type.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Subscriber:
    """A registered individual, identified by mobile number and KYC proof."""

    subscriber_id: str
    mobile_number: str
    identity_proof_ref: str
    created_at: datetime
