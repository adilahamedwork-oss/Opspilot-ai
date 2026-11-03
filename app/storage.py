import json
import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DATABASE_PATH", "/data/opspilot.db")


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                severity TEXT NOT NULL,
                mode TEXT NOT NULL,
                provider TEXT NOT NULL,
                summary TEXT NOT NULL,
                report TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_incident(result: dict):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO incidents (
                incident_id, service, severity, mode,
                provider, summary, report
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            result["incident_id"],
            result["service"],
            result["severity"],
            result["mode"],
            result["provider"],
            result["summary"],
            json.dumps(result),
        ))


def get_incidents(limit: int = 50):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT incident_id, service, severity, mode,
                   provider, summary, created_at
            FROM incidents
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]


def get_incident(incident_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT report FROM incidents WHERE incident_id = ?",
            (incident_id,)
        ).fetchone()
        return json.loads(row["report"]) if row else None


def get_incident_stats():
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM incidents"
        ).fetchone()[0]

        severity = conn.execute("""
            SELECT severity, COUNT(*) AS count
            FROM incidents GROUP BY severity
        """).fetchall()

        modes = conn.execute("""
            SELECT mode, COUNT(*) AS count
            FROM incidents GROUP BY mode
        """).fetchall()

        return {
            "total": total,
            "severity": {r["severity"]: r["count"] for r in severity},
            "modes": {r["mode"]: r["count"] for r in modes}
        }
