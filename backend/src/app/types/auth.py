"""User and Principal domain types for auth (E1-S4).

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass
from datetime import datetime

from app.types.enums import Role


@dataclass(frozen=True)
class User:
    """A persisted account backing login (staff seeded; subscribers implicit)."""

    user_id: str
    role: Role
    username: str | None
    password_hash: str | None
    mobile_number: str | None
    subscriber_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class Principal:
    """A verified, decoded-token identity attached to each authenticated request."""

    user_id: str
    role: Role
    subscriber_id: str | None
