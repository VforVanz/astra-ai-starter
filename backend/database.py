"""SQLite helpers for the ASTRA AI starter backend."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "astra_ai.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                event_type TEXT NOT NULL,
                username TEXT,
                outcome TEXT,
                raw_json TEXT NOT NULL,
                ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                window_start TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                event_type TEXT NOT NULL,
                risk TEXT NOT NULL,
                evidence TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(rule_id, source_ip, window_start)
            );
            """
        )


def insert_events(events: list[dict[str, Any]]) -> int:
    """Insert events, ignoring exact duplicates. Returns number newly inserted."""
    import hashlib

    inserted = 0
    with get_connection() as conn:
        for event in events:
            canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
            fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            cursor = conn.execute(
                """INSERT OR IGNORE INTO events
                   (fingerprint, timestamp, source_ip, event_type, username, outcome, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    fingerprint,
                    event["timestamp"],
                    event["source_ip"],
                    event["event_type"],
                    event.get("username"),
                    event.get("outcome"),
                    canonical,
                ),
            )
            inserted += cursor.rowcount
    return inserted


def fetch_events() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT timestamp, source_ip, event_type, username, outcome, raw_json FROM events ORDER BY timestamp"
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["raw"] = json.loads(item.pop("raw_json"))
        result.append(item)
    return result


def create_alert(alert: dict[str, Any]) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO alerts
               (rule_id, timestamp, window_start, source_ip, event_type, risk, evidence, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
            (
                alert["rule_id"], alert["timestamp"], alert["window_start"],
                alert["source_ip"], alert["event_type"], alert["risk"], alert["evidence"],
            ),
        )
        return cursor.rowcount == 1


def list_alerts() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, timestamp, source_ip, event_type, risk, evidence, status FROM alerts ORDER BY timestamp DESC, id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_alert(alert_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, rule_id, timestamp, window_start, source_ip, event_type, risk, evidence, status, created_at FROM alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()
    return dict(row) if row else None


def update_alert_status(alert_id: int, status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("UPDATE alerts SET status = ? WHERE id = ?", (status, alert_id))
        return cursor.rowcount > 0


def dashboard_summary() -> dict[str, int]:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        high = conn.execute("SELECT COUNT(*) FROM alerts WHERE risk = 'high'").fetchone()[0]
        open_incidents = conn.execute("SELECT COUNT(*) FROM alerts WHERE status != 'resolved'").fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return {
        "total_alerts": total,
        "high_risk_alerts": high,
        "open_incidents": open_incidents,
        "events_ingested": events,
    }
