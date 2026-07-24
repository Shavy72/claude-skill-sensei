"""Smoke tests for sensei_mcp.db.

Three tests:
1. init — DB + all 6 tables are created
2. record_pattern + get_patterns — UPSERT + return value correct
3. idle-calc — get_idle_seconds returns a small value after record_activity

Uses tmp_path + monkeypatch to avoid touching the production DB.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sensei_mcp.db import (
    get_idle_seconds,
    get_patterns,
    init_db,
    record_activity,
    record_pattern,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirects SENSEI_DB_PATH to a temporary file and initializes the schema."""
    db_file = tmp_path / "test_sensei.db"
    monkeypatch.setenv("SENSEI_DB_PATH", str(db_file))
    init_db()


# ---------------------------------------------------------------------------
# Test 1: init — tables present
# ---------------------------------------------------------------------------


def test_init_creates_tables() -> None:
    """init_db() must create all 6 tables without exception."""
    import os
    import sqlite3

    db_path = os.environ["SENSEI_DB_PATH"]
    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()

    expected = {
        "last_activity",
        "project_profiles",
        "patterns",
        "audit_log",
        "anger_levels",
        "why_answers",
    }
    missing = expected - tables
    assert not missing, f"Missing tables: {missing}"


# ---------------------------------------------------------------------------
# Test 2: record_pattern + get_patterns
# ---------------------------------------------------------------------------


def test_record_and_get_patterns() -> None:
    """record_pattern() should increment the counter via UPSERT; get_patterns() returns the list."""
    project = "test-project"
    pattern = "missing-type-hints"

    c1 = record_pattern(project, pattern)
    assert c1 == 1, f"First call: counter should be 1, is {c1}"

    c2 = record_pattern(project, pattern)
    assert c2 == 2, f"Second call: counter should be 2, is {c2}"

    patterns = get_patterns(project)
    assert len(patterns) == 1
    assert patterns[0]["pattern_id"] == pattern
    assert patterns[0]["counter"] == 2


# ---------------------------------------------------------------------------
# Test 3: idle-calc
# ---------------------------------------------------------------------------


def test_idle_seconds_after_activity() -> None:
    """get_idle_seconds() must return a value close to 0 right after record_activity()."""
    record_activity(
        project_path="/tmp/test-project",
        action_type="test_run",
        payload={"files": 3},
    )
    idle = get_idle_seconds()
    assert 0 <= idle < 5, (
        f"Idle should be close to 0 right after record_activity, is {idle}s"
    )
