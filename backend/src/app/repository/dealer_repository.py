"""Read access to the seeded DealerMaster table (E2-S1).

Repository layer — imports Types and Config only.

Rows are seeded declaratively by repository/schema.sql (applied via
apply_schema); this module only reads, matching the story's own scope
("no dealer-facing UI" — no create/update path is needed here).
"""

import sqlite3

from app.types.dealer import DealerMaster


def get_dealer_by_code(connection: sqlite3.Connection, dealer_code: str) -> DealerMaster | None:
    """Return the dealer with dealer_code, or None if not found.

    Used by the activation engine (a later story) to validate a dealer
    code against the seeded master, including the DEALER-FAIL sentinel.
    """
    row = connection.execute(
        "SELECT dealer_code, dealer_name, active FROM dealer_master WHERE dealer_code = ?",
        (dealer_code,),
    ).fetchone()
    if row is None:
        return None
    code, name, active = row
    return DealerMaster(dealer_code=str(code), dealer_name=str(name), active=bool(active))
