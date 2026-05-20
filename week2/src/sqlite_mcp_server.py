from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from fastmcp import FastMCP


mcp = FastMCP("SQLite-Service")


def _db_path(db_path: str | None = None) -> Path:
    raw_path = (db_path or "").strip() or os.environ.get("TAG_DATA_DB_PATH", "").strip()
    if raw_path:
        return Path(raw_path).expanduser()
    return Path.cwd() / "jobs.db"


def _fetch_pending_rows(after_rowid: int, batch_size: int, db_path: str | None = None) -> list[dict[str, object]]:
    resolved_db_path = _db_path(db_path)
    if not resolved_db_path.exists():
        return []

    with sqlite3.connect(resolved_db_path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT rowid, source_id, job_title, description
            FROM jobs
            WHERE rowid > ?
              AND (tech_stack IS NULL OR TRIM(tech_stack) = '')
            ORDER BY rowid
            LIMIT ?
            """,
            (after_rowid, batch_size),
        )
        return [dict(row) for row in cursor.fetchall()]


@mcp.tool
def fetch_pending_jobs(after_rowid: int = 0, batch_size: int = 5, db_path: str = "") -> list[dict[str, object]]:
    """Return the next batch of jobs that still need tech stack tagging."""
    return _fetch_pending_rows(after_rowid, batch_size, db_path)


@mcp.tool
def update_tech_stack(source_id: str, tech_stack: str, db_path: str = "") -> dict[str, object]:
    """Persist the generated tech stack for a single job row."""
    resolved_db_path = _db_path(db_path)
    if not resolved_db_path.exists():
        return {"ok": False, "error": f"Database not found: {resolved_db_path}"}

    try:
        with sqlite3.connect(resolved_db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET tech_stack = ?
                WHERE source_id = ?
                  AND (tech_stack IS NULL OR TRIM(tech_stack) = '')
                """,
                (tech_stack, source_id),
            )
            connection.commit()
            return {"ok": True, "updated": cursor.rowcount}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool
def count_pending_jobs(db_path: str = "") -> dict[str, object]:
    """Return the number of jobs that still need tagging."""
    resolved_db_path = _db_path(db_path)
    if not resolved_db_path.exists():
        return {"ok": False, "error": f"Database not found: {resolved_db_path}"}

    try:
        with sqlite3.connect(resolved_db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                WHERE tech_stack IS NULL OR TRIM(tech_stack) = ''
                """
            )
            row = cursor.fetchone()
            return {"ok": True, "count": int(row[0] if row else 0)}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}


if __name__ == "__main__":
    mcp.run()