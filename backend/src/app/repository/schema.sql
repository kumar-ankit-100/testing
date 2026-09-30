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
