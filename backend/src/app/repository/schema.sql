-- TelcoLane SQLite schema.
--
-- Append-only tables are protected by BEFORE UPDATE/DELETE triggers as
-- defense-in-depth (system-design.md 5.2); the primary enforcement is that
-- no update/delete function is exposed by the corresponding repository
-- module. Money columns are stored as TEXT (canonical str(Decimal)) and
-- reconstructed as Decimal on read (system-design.md 5.5).
--
-- Grown incrementally: each repository story below adds only its own
-- table(s) and triggers to this same file (schema.sql is a documented
-- cross-cutting file per component-map.md).

-- E1-S4: users — backs POST /api/auth/login (not implemented this group).
-- Staff (csr/admin/dealer) rows are seeded elsewhere; subscriber rows are
-- created implicitly by registration (E2-S2, a later group).
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('subscriber', 'csr', 'admin', 'dealer')),
    username TEXT UNIQUE,
    password_hash TEXT,
    mobile_number TEXT,
    subscriber_id TEXT,
    created_at TEXT NOT NULL
);

-- E2-S1: subscribers, subscriptions, dealer_master.
CREATE TABLE IF NOT EXISTS subscribers (
    subscriber_id TEXT PRIMARY KEY,
    mobile_number TEXT NOT NULL,
    identity_proof_ref TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id TEXT PRIMARY KEY,
    subscriber_id TEXT NOT NULL REFERENCES subscribers (subscriber_id),
    mobile_number TEXT NOT NULL,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('PREPAID', 'POSTPAID')),
    state TEXT NOT NULL CHECK (
        state IN (
            'PENDING_KYC', 'ACTIVE', 'SUSPENDED', 'TERMINATED',
            'PORT_OUT_REQUESTED', 'PORTED_OUT'
        )
    ),
    current_plan_version_id TEXT,
    dealer_code TEXT,
    created_at TEXT NOT NULL,
    activated_at TEXT,
    updated_at TEXT NOT NULL
);

-- NFR-07 / E2-S1 AC-2: at most one ACTIVE subscription per mobile number,
-- enforced at the database level (the service layer also checks this
-- before insert; this index is the authoritative guard under a race).
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_active_mobile
    ON subscriptions (mobile_number)
    WHERE state = 'ACTIVE';

CREATE TABLE IF NOT EXISTS dealer_master (
    dealer_code TEXT PRIMARY KEY,
    dealer_name TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0, 1))
);

-- E2-S1 AC-3: seeded with >= 5 valid dealer codes plus the DEALER-FAIL
-- sentinel, applied idempotently on every schema apply.
INSERT OR IGNORE INTO dealer_master (dealer_code, dealer_name, active) VALUES
    ('DLR-BLR-001', 'Bengaluru Central Retail', 1),
    ('DLR-DEL-002', 'Delhi Connaught Place Outlet', 1),
    ('DLR-MUM-003', 'Mumbai Andheri Franchise', 1),
    ('DLR-CHN-004', 'Chennai T Nagar Store', 1),
    ('DLR-HYD-005', 'Hyderabad Gachibowli Kiosk', 1),
    ('DEALER-FAIL', 'Sentinel dealer code — always rejected by design', 0);

-- E3-S1: plan_versions — append-only, immutable once published.
-- The only mutator exposed by plan_repository.py is publish_plan_version
-- (draft -> published, once); no update_plan_version/delete_plan_version
-- function exists at all (system-design.md 5.2). These triggers are
-- defense-in-depth against a raw SQL bypass of that repository boundary.
CREATE TABLE IF NOT EXISTS plan_versions (
    plan_version_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('PREPAID', 'POSTPAID')),
    version_number INTEGER NOT NULL,
    price TEXT NOT NULL,
    terms TEXT NOT NULL,
    published INTEGER NOT NULL DEFAULT 0 CHECK (published IN (0, 1)),
    created_at TEXT NOT NULL,
    published_at TEXT
);

CREATE TRIGGER IF NOT EXISTS trg_plan_versions_immutable_once_published
BEFORE UPDATE ON plan_versions
WHEN OLD.published = 1
BEGIN
    SELECT RAISE(ABORT, 'plan_versions: cannot modify a published plan version');
END;

CREATE TRIGGER IF NOT EXISTS trg_plan_versions_no_delete
BEFORE DELETE ON plan_versions
BEGIN
    SELECT RAISE(ABORT, 'plan_versions: rows are append-only, delete is not permitted');
END;

-- E4-S1: billing_records — fully append-only (no update path ever, unlike
-- plan_versions' one-time publish flip). Money columns stored as TEXT,
-- reconstructed as Decimal on read (system-design.md 5.5).
CREATE TABLE IF NOT EXISTS billing_records (
    billing_record_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES subscriptions (subscription_id),
    from_plan_version_id TEXT,
    to_plan_version_id TEXT NOT NULL,
    pro_rata_amount TEXT NOT NULL,
    charges_total TEXT NOT NULL,
    billing_period_start TEXT NOT NULL,
    billing_period_end TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS trg_billing_records_no_update
BEFORE UPDATE ON billing_records
BEGIN
    SELECT RAISE(ABORT, 'billing_records: rows are append-only, update is not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_billing_records_no_delete
BEFORE DELETE ON billing_records
BEGIN
    SELECT RAISE(ABORT, 'billing_records: rows are append-only, delete is not permitted');
END;

-- E5-S1: state_transitions — fully append-only, same shape as billing_records.
CREATE TABLE IF NOT EXISTS state_transitions (
    transition_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES subscriptions (subscription_id),
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    reason_code TEXT,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS trg_state_transitions_no_update
BEFORE UPDATE ON state_transitions
BEGIN
    SELECT RAISE(ABORT, 'state_transitions: rows are append-only, update is not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_state_transitions_no_delete
BEFORE DELETE ON state_transitions
BEGIN
    SELECT RAISE(ABORT, 'state_transitions: rows are append-only, delete is not permitted');
END;

-- E5-S1: port_out_events — append-only in the sense that rows are never
-- deleted, but UPDATE is allowed once (close_port_out_event sets an end
-- status + closed_at) — so only a DELETE trigger is added, not an UPDATE
-- one (system-design.md 5.2 / E5-S1 AC-2).
CREATE TABLE IF NOT EXISTS port_out_events (
    port_out_event_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES subscriptions (subscription_id),
    requested_at TEXT NOT NULL,
    cooling_period_end_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'CANCELLED_WITHIN_WINDOW', 'FINALIZED')),
    closed_at TEXT
);

CREATE TRIGGER IF NOT EXISTS trg_port_out_events_no_delete
BEFORE DELETE ON port_out_events
BEGIN
    SELECT RAISE(ABORT, 'port_out_events: rows are never deleted, only closed');
END;

-- E6-S1: csr_overrides — fully append-only audit trail, same shape as
-- billing_records/state_transitions. actor, reason_code, and created_at
-- are NOT NULL at the DB level, matching the CSROverride dataclass's
-- non-Optional str fields (AC-2).
CREATE TABLE IF NOT EXISTS csr_overrides (
    override_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES subscriptions (subscription_id),
    actor TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    overridden_action TEXT NOT NULL CHECK (overridden_action IN ('ACTIVATION', 'PLAN_CHANGE')),
    original_rejection_reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS trg_csr_overrides_no_update
BEFORE UPDATE ON csr_overrides
BEGIN
    SELECT RAISE(ABORT, 'csr_overrides: rows are append-only, update is not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_csr_overrides_no_delete
BEFORE DELETE ON csr_overrides
BEGIN
    SELECT RAISE(ABORT, 'csr_overrides: rows are append-only, delete is not permitted');
END;
