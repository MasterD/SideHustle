"""SQLite storage. Every operation opens its own connection for safe HTTP threads."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    settings_json TEXT NOT NULL,
    website_draft_json TEXT NOT NULL,
    website_published_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS services (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    price REAL NOT NULL,
    active INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    message TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    value REAL NOT NULL,
    commission_rate REAL NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    service_id TEXT NOT NULL REFERENCES services(id),
    service_name TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    lead_id TEXT NOT NULL REFERENCES leads(id),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    channels_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS published_posts (
    post_id TEXT PRIMARY KEY REFERENCES posts(id),
    company_id TEXT NOT NULL REFERENCES companies(id),
    snapshot_json TEXT NOT NULL,
    published_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id),
    name TEXT NOT NULL,
    objective TEXT NOT NULL,
    offer TEXT NOT NULL,
    planned_budget REAL NOT NULL,
    channels_json TEXT NOT NULL,
    status TEXT NOT NULL,
    source_code TEXT UNIQUE NOT NULL,
    post_id TEXT REFERENCES posts(id),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS deliveries (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id),
    post_id TEXT NOT NULL REFERENCES posts(id),
    title TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(post_id, channel, content_hash)
);
CREATE TABLE IF NOT EXISTS activity (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS leads_company ON leads(company_id, created_at);
CREATE INDEX IF NOT EXISTS bookings_company ON bookings(company_id, start_at);
CREATE INDEX IF NOT EXISTS posts_company ON posts(company_id, created_at);
CREATE INDEX IF NOT EXISTS published_posts_company ON published_posts(company_id, published_at);
CREATE INDEX IF NOT EXISTS campaigns_company ON campaigns(company_id, created_at);
CREATE INDEX IF NOT EXISTS deliveries_company ON deliveries(company_id, created_at);
CREATE INDEX IF NOT EXISTS activity_company ON activity(company_id, created_at);
"""


class Database:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).resolve().parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(SCHEMA)

    @contextmanager
    def connection(self, write=False):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        try:
            # Acquire the write lock before checking a slot. Two concurrent
            # requests cannot both observe the same free appointment.
            if write:
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            if write:
                connection.commit()
        except Exception:
            if write:
                connection.rollback()
            raise
        finally:
            connection.close()


def initialize_database(path):
    return Database(path)
