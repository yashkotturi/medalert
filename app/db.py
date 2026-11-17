"""Database layer: SQLite connection, schema and seed data.

Why SQLite? Zero setup, a single file, perfect for a small service.
Trade-off: it locks the whole database on writes, so it does not suit many
concurrent writers or multiple replicas. In production you would move to
PostgreSQL. (Good interview talking point.)
"""

import sqlite3
from contextlib import contextmanager

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS wards (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    total_beds INTEGER NOT NULL CHECK (total_beds > 0),
    occupied_beds INTEGER NOT NULL CHECK (occupied_beds >= 0),
    CHECK (occupied_beds <= total_beds)
);

CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    min_quantity INTEGER NOT NULL CHECK (min_quantity >= 0),
    unit TEXT NOT NULL DEFAULT 'units'
);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('P1','P2','P3','P4')),
    details TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','in_progress','resolved')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Audit log: who changed what, when. Required for healthcare and ITSM.
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# Fake data only. Never put real patient information in a demo project.
SEED_WARDS = [
    ("ICU", 20, 18),
    ("General Ward A", 40, 22),
    ("Pediatrics", 25, 24),
    ("Emergency", 15, 9),
]

SEED_MEDICINES = [
    ("Paracetamol 500mg", 1200, 300, "tablets"),
    ("Insulin (Regular)", 40, 50, "vials"),
    ("Amoxicillin 250mg", 500, 200, "capsules"),
    ("Oxygen Cylinder", 6, 10, "cylinders"),
    ("Saline 0.9% 500ml", 300, 100, "bags"),
]


@contextmanager
def get_conn():
    """Open a connection, commit on success, roll back on error, always close."""
    conn = sqlite3.connect(config.DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(seed: bool = True) -> None:
    """Create tables, and add seed data only if the tables are empty."""
    with get_conn() as conn:
        # WAL mode lets reads continue while a write is happening.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        if seed and conn.execute("SELECT COUNT(*) FROM wards").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO wards (name, total_beds, occupied_beds) VALUES (?, ?, ?)",
                SEED_WARDS,
            )
            conn.executemany(
                "INSERT INTO medicines (name, quantity, min_quantity, unit) "
                "VALUES (?, ?, ?, ?)",
                SEED_MEDICINES,
            )


def audit(conn: sqlite3.Connection, actor: str, action: str, details: str) -> None:
    conn.execute(
        "INSERT INTO audit_log (actor, action, details) VALUES (?, ?, ?)",
        (actor, action, details),
    )
