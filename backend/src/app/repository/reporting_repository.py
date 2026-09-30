"""Read-only aggregation queries for admin reporting (E7-S1).

Repository layer — imports Types and Config only.

Data-model note (documented, not a bug): a rejected activation attempt
writes no row anywhere (system-design.md 3.1) — the subscription simply
stays PENDING_KYC, with no persisted signal distinguishing "never
attempted" from "rejected at KYC" from "rejected at dealer" from
"rejected at MNP". activation_funnel_counts therefore reports the same
count for kyc_passed/dealer_passed/mnp_passed as for activated: every
subscription that ever reached ACTIVE. This still satisfies AC-2 (each
stage <= the prior stage, which holds under equality) without fabricating
a distinction the stored data cannot support.
"""

import sqlite3
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

_CHURN_STATES = ("PORTED_OUT", "TERMINATED")


def activation_funnel_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """Return counts per funnel stage: registered, kyc_passed, dealer_passed,
    mnp_passed, activated (AC-2). See module docstring for why the three
    middle stages equal `activated`.
    """
    registered = connection.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
    activated = connection.execute(
        "SELECT COUNT(DISTINCT subscription_id) FROM state_transitions WHERE to_state = 'ACTIVE'"
    ).fetchone()[0]
    return {
        "registered": int(registered),
        "kyc_passed": int(activated),
        "dealer_passed": int(activated),
        "mnp_passed": int(activated),
        "activated": int(activated),
    }


def plan_mix_distribution(connection: sqlite3.Connection) -> dict[str, int]:
    """Return the count of currently-ACTIVE subscriptions per plan_type."""
    rows = connection.execute(
        "SELECT plan_type, COUNT(*) FROM subscriptions WHERE state = 'ACTIVE' "
        "GROUP BY plan_type"
    ).fetchall()
    return {str(plan_type): int(count) for plan_type, count in rows}


def monthly_churn_rate(connection: sqlite3.Connection) -> dict[str, Decimal]:
    """Return, per calendar month with at least one churn event, the count
    of PORTED_OUT/TERMINATED transitions in that month divided by the
    active base at that month's start (AC-3).
    """
    months = _distinct_churn_months(connection)
    return {month: _churn_rate_for_month(connection, month) for month in months}


def arpu_trend(connection: sqlite3.Connection) -> dict[str, Decimal]:
    """Return, per calendar month with at least one billing record, the
    stubbed ARPU = SUM(charges_total) / COUNT(DISTINCT subscription_id)
    for that month, as Decimal (AC-4).
    """
    rows = connection.execute(
        """
        SELECT strftime('%Y-%m', created_at) AS month,
               charges_total,
               subscription_id
        FROM billing_records
        """
    ).fetchall()

    totals: dict[str, Decimal] = {}
    subscriber_counts: dict[str, set[str]] = {}
    for month, charges_total, subscription_id in rows:
        totals[month] = totals.get(month, Decimal("0.00")) + Decimal(str(charges_total))
        subscriber_counts.setdefault(month, set()).add(str(subscription_id))

    return {
        month: (totals[month] / len(subscriber_counts[month])).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        for month in totals
    }


def _distinct_churn_months(connection: sqlite3.Connection) -> list[str]:
    placeholders = ", ".join("?" for _ in _CHURN_STATES)
    rows = connection.execute(
        f"""
        SELECT DISTINCT strftime('%Y-%m', created_at) AS month
        FROM state_transitions
        WHERE to_state IN ({placeholders})
        ORDER BY month ASC
        """,
        _CHURN_STATES,
    ).fetchall()
    return [str(row[0]) for row in rows]


def _churn_rate_for_month(connection: sqlite3.Connection, month: str) -> Decimal:
    month_start = datetime.strptime(month, "%Y-%m").replace(tzinfo=UTC)
    active_base = _active_base_before(connection, month_start.isoformat())
    if active_base == 0:
        return Decimal("0.00")

    placeholders = ", ".join("?" for _ in _CHURN_STATES)
    churned = connection.execute(
        f"""
        SELECT COUNT(*) FROM state_transitions
        WHERE to_state IN ({placeholders}) AND strftime('%Y-%m', created_at) = ?
        """,
        (*_CHURN_STATES, month),
    ).fetchone()[0]

    return (Decimal(churned) / Decimal(active_base)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _active_base_before(connection: sqlite3.Connection, cutoff_iso: str) -> int:
    """Count subscriptions whose most recent transition before cutoff_iso
    left them in ACTIVE state (a point-in-time reconstruction from the
    state_transitions event log).
    """
    row = connection.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT st.subscription_id, st.to_state
            FROM state_transitions st
            WHERE st.created_at < ?
              AND st.created_at = (
                  SELECT MAX(st2.created_at) FROM state_transitions st2
                  WHERE st2.subscription_id = st.subscription_id AND st2.created_at < ?
              )
        )
        WHERE to_state = 'ACTIVE'
        """,
        (cutoff_iso, cutoff_iso),
    ).fetchone()
    return int(row[0])
