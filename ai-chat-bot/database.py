"""
Database setup for the IT Asset Chatbot.

Two tables:
  - assets:          individually tracked items (computers, monitors, monitor
                      arms, docks). Each row is one physical unit with a
                      serial number, who it's assigned to, and its status.
  - cable_inventory:  bulk-tracked items (cables). Tracked by quantity rather
                      than by serial number, since cables aren't usually
                      individually asset-tagged.

"Desk / office setups" are NOT a separate table. A person's full setup is
just every row in `assets` where assigned_to = that person. This keeps the
schema simple and lets the chatbot answer "what's on Jane's desk?" with a
plain filter instead of maintaining a separate bundling table.

Swap the SEED data for a real export later by writing a loader that inserts
into these same two tables (see seed_data.py for the shape expected).
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "assets.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type      TEXT NOT NULL CHECK (asset_type IN ('computer','monitor','monitor_arm','dock')),
    make            TEXT,
    model           TEXT,
    serial_number   TEXT UNIQUE,
    assigned_to     TEXT,
    assigned_email  TEXT,
    department      TEXT,
    status          TEXT NOT NULL CHECK (status IN ('assigned','available','in_repair','retired')),
    location        TEXT,
    purchase_date   TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS cable_inventory (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cable_type          TEXT NOT NULL,
    description         TEXT,
    quantity_total      INTEGER NOT NULL DEFAULT 0,
    quantity_available  INTEGER NOT NULL DEFAULT 0,
    location            TEXT
);

CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_assigned_to ON assets(assigned_to);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
"""


def get_connection(read_only: bool = False) -> sqlite3.Connection:
    if read_only:
        uri = f"file:{DB_PATH}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_schema_description() -> str:
    """Human/LLM-readable schema description used in the NL->SQL prompt."""
    return """
Table: assets
  id              INTEGER, primary key
  asset_type      TEXT, one of: 'computer', 'monitor', 'monitor_arm', 'dock'
  make            TEXT, e.g. 'Dell', 'Apple', 'Logitech'
  model           TEXT, e.g. 'Latitude 5440', 'UltraSharp U2723QE'
  serial_number   TEXT, unique serial/asset tag
  assigned_to     TEXT, employee full name this item is assigned to (NULL if not assigned / in stock)
  assigned_email  TEXT, employee email
  department      TEXT, employee's department, e.g. 'Engineering', 'Sales', 'IT'
  status          TEXT, one of: 'assigned', 'available', 'in_repair', 'retired'
  location        TEXT, office/building/desk code
  purchase_date   TEXT, ISO date string
  notes           TEXT

Table: cable_inventory
  id                  INTEGER, primary key
  cable_type          TEXT, e.g. 'HDMI', 'USB-C to USB-C', 'DisplayPort', 'Ethernet (Cat6)', 'USB-A to Lightning'
  description         TEXT
  quantity_total      INTEGER, total owned
  quantity_available  INTEGER, currently in stock / not checked out
  location            TEXT

Notes for query generation:
  - A person's "desk setup" / "office setup" = all rows in `assets` where assigned_to matches their name.
  - "How many X do we have left" for computers/monitors/arms/docks means COUNT(*) FROM assets WHERE asset_type = 'X' AND status = 'available'.
  - "How many X do we have left" for cables means SUM(quantity_available) FROM cable_inventory WHERE cable_type LIKE '%X%'.
  - Name matching should be case-insensitive and tolerant of partial names (use LIKE).
"""


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
