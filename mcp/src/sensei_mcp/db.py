"""SQLite layer for Sensei MCP.

No MCP knowledge here — only pure data operations.
DB path: ~/.claude/sensei/state/sensei.db (auto-create via SENSEI_DB_PATH or default).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DB path
# ---------------------------------------------------------------------------


def get_db_path() -> Path:
    """Returns the configured DB path (env SENSEI_DB_PATH or default)."""
    env = os.environ.get("SENSEI_DB_PATH")
    if env:
        return Path(env)
    return Path.home() / ".claude" / "sensei" / "state" / "sensei.db"


def get_connection() -> sqlite3.Connection:
    """Opens (and creates if needed) the SQLite connection with row factory."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema init
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS last_activity (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT    NOT NULL,
    action_type  TEXT    NOT NULL,
    payload      TEXT,
    ts           REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS project_profiles (
    repo_hash    TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    profile_yaml TEXT,
    stage        TEXT,
    stack        TEXT,
    updated_at   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS patterns (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project    TEXT NOT NULL,
    pattern_id TEXT NOT NULL,
    counter    INTEGER NOT NULL DEFAULT 1,
    last_seen  REAL    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'watch',
    UNIQUE (project, pattern_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    project      TEXT NOT NULL,
    severity     TEXT NOT NULL,
    message      TEXT NOT NULL,
    action_taken TEXT
);

CREATE TABLE IF NOT EXISTS anger_levels (
    project    TEXT NOT NULL,
    pattern_id TEXT NOT NULL,
    counter    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (project, pattern_id)
);

CREATE TABLE IF NOT EXISTS why_answers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    depth       INTEGER NOT NULL,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    captured_at REAL NOT NULL
);
"""


def init_db() -> None:
    """Creates all tables if they do not already exist."""
    with get_connection() as conn:
        conn.executescript(_DDL)
    logger.info("DB initialized: %s", get_db_path())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def repo_hash(project_path: str) -> str:
    """SHA-256 hash of the absolute project path (first 16 hex chars).

    Args:
        project_path: Absolute or relative path — resolved to absolute internally.

    Returns:
        16-character hex string.
    """
    abs_path = str(Path(project_path).resolve())
    return hashlib.sha256(abs_path.encode()).hexdigest()[:16]


def _now() -> float:
    """Unix timestamp as float."""
    return time.time()


# ---------------------------------------------------------------------------
# last_activity
# ---------------------------------------------------------------------------


def record_activity(project_path: str, action_type: str, payload: Any = None) -> None:
    """Writes an activity entry into last_activity.

    Args:
        project_path: Absolute or relative path to the project root.
        action_type:  Free-text label for the action (e.g. "file_edit", "test_run").
        payload:      Optional JSON-serializable payload.
    """
    payload_str = json.dumps(payload) if payload is not None else None
    ts = _now()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO last_activity (project_path, action_type, payload, ts) VALUES (?, ?, ?, ?)",
            (project_path, action_type, payload_str, ts),
        )
    logger.debug(
        "record_activity project=%s action=%s ts=%.3f", project_path, action_type, ts
    )


def get_last_activity(project_path: str | None = None) -> sqlite3.Row | None:
    """Returns the most recent activity entry.

    Args:
        project_path: If given, only entries for this project.

    Returns:
        sqlite3.Row with fields id, project_path, action_type, payload, ts — or None.
    """
    with get_connection() as conn:
        if project_path:
            return conn.execute(
                "SELECT * FROM last_activity WHERE project_path=? ORDER BY ts DESC LIMIT 1",
                (project_path,),
            ).fetchone()
        return conn.execute(
            "SELECT * FROM last_activity ORDER BY ts DESC LIMIT 1"
        ).fetchone()


def get_idle_seconds() -> int:
    """Seconds since the last recorded activity (system-wide).

    Returns:
        Number of seconds as int. 0 if no activity has ever been recorded.
    """
    row = get_last_activity()
    if row is None:
        return 0
    return max(0, int(_now() - row["ts"]))


# ---------------------------------------------------------------------------
# project_profiles
# ---------------------------------------------------------------------------


def get_project_profile(project_path: str) -> dict | None:
    """Loads the stored profile for a project path.

    Args:
        project_path: Path to the project root.

    Returns:
        Dict with repo_hash, project_path, profile_yaml, stage, stack, updated_at
        or None if no entry exists.
    """
    rh = repo_hash(project_path)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM project_profiles WHERE repo_hash=?", (rh,)
        ).fetchone()
    return dict(row) if row else None


def upsert_project_profile(
    project_path: str,
    profile_yaml: str,
    stage: str,
    stack: str,
) -> None:
    """Writes or updates a project's profile.

    Args:
        project_path: Path to the project root (gets hashed).
        profile_yaml: YAML string with the profile content.
        stage:        Current development stage (e.g. "warmup", "production").
        stack:        Tech stack as free text (e.g. "Python, SQLite, Flask").
    """
    rh = repo_hash(project_path)
    ts = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO project_profiles (repo_hash, project_path, profile_yaml, stage, stack, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_hash) DO UPDATE SET
                profile_yaml=excluded.profile_yaml,
                stage=excluded.stage,
                stack=excluded.stack,
                updated_at=excluded.updated_at
            """,
            (rh, project_path, profile_yaml, stage, stack, ts),
        )
    logger.debug("upsert_project_profile repo_hash=%s stage=%s", rh, stage)


# ---------------------------------------------------------------------------
# patterns
# ---------------------------------------------------------------------------


def record_pattern(project: str, pattern_id: str) -> int:
    """Increments the counter for a pattern (INSERT or UPDATE via UPSERT).

    Args:
        project:    Project identifier (e.g. path or short name).
        pattern_id: Unique pattern name (e.g. "missing-type-hints").

    Returns:
        New counter value after the increment.
    """
    ts = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO patterns (project, pattern_id, counter, last_seen, status)
            VALUES (?, ?, 1, ?, 'watch')
            ON CONFLICT(project, pattern_id) DO UPDATE SET
                counter=counter+1,
                last_seen=excluded.last_seen
            """,
            (project, pattern_id, ts),
        )
        row = conn.execute(
            "SELECT counter FROM patterns WHERE project=? AND pattern_id=?",
            (project, pattern_id),
        ).fetchone()
    counter = row["counter"] if row else 1
    logger.debug(
        "record_pattern project=%s pattern=%s counter=%d", project, pattern_id, counter
    )
    return counter


def get_patterns(project: str) -> list[dict]:
    """Returns all patterns of a project, sorted by counter DESC.

    Args:
        project: Project identifier.

    Returns:
        List of dicts with id, project, pattern_id, counter, last_seen, status.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM patterns WHERE project=? ORDER BY counter DESC",
            (project,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# why_answers
# ---------------------------------------------------------------------------


def record_why_chain(project: str, answers: list[dict]) -> None:
    """Stores a why-chain (list of question-answer pairs with depth).

    Args:
        project: Project identifier.
        answers: List of dicts with fields depth (int), question (str), answer (str).
    """
    ts = _now()
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO why_answers (project, depth, question, answer, captured_at) VALUES (?, ?, ?, ?, ?)",
            [(project, a["depth"], a["question"], a["answer"], ts) for a in answers],
        )
    logger.debug("record_why_chain project=%s entries=%d", project, len(answers))


def get_why_chain(project: str) -> list[dict]:
    """Loads the most recent why-chain of a project (latest captured_at batch).

    Args:
        project: Project identifier.

    Returns:
        List of dicts with id, project, depth, question, answer, captured_at,
        sorted by depth ASC.
    """
    with get_connection() as conn:
        ts_row = conn.execute(
            "SELECT MAX(captured_at) AS latest FROM why_answers WHERE project=?",
            (project,),
        ).fetchone()
        if not ts_row or ts_row["latest"] is None:
            return []
        latest_ts = ts_row["latest"]
        rows = conn.execute(
            "SELECT * FROM why_answers WHERE project=? AND captured_at >= ? ORDER BY depth ASC",
            (project, latest_ts - 1.0),
        ).fetchall()
    return [dict(r) for r in rows]
