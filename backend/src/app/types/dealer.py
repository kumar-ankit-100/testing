"""DealerMaster domain type.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DealerMaster:
    """A seeded dealer code consulted by the activation engine."""

    dealer_code: str
    dealer_name: str
    active: bool
