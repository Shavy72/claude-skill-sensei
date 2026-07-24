"""activity_tracker.py - Sensei PostToolUse hook.

Caller: PostToolUse hook in ~/.claude/settings.json (payload on stdin), or a direct CLI test.
Schema:
  Input (stdin): {tool_name: str, tool_input: {command?: str, file_path?: str}, cwd: str}
  last_activity.json: {timestamp: ISO, project_path: str, tool_name: str, action_type: str}
  patterns.json:      {"<proj_hash>": {"<pattern_id>": int, ...}, ...}
  inbox.json:         [{ts: ISO, pattern: str, severity: str, detail: str}, ...]

Environment:
  SENSEI_HOME         override for the runtime directory (default: ~/.claude/sensei)
  SENSEI_RUN_PROCESS  name of your long-running job process; when unset, the
                      "push during an active run" pattern stays disabled
  SENSEI_PROD_DB      filename of the production database that must not be
                      hand-edited (default: production.db)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths + configuration
# ---------------------------------------------------------------------------
SENSEI_HOME = Path(
    os.environ.get("SENSEI_HOME") or (Path.home() / ".claude" / "sensei")
)
STATE_DIR = SENSEI_HOME / "state"
LAST_ACT = STATE_DIR / "last_activity.json"
PATTERNS = STATE_DIR / "patterns.json"
INBOX = STATE_DIR / "inbox.json"
ACTIVITY_LOG = STATE_DIR / "activity.log"

# Name of the long-running job process to guard against (e.g. "nightly_runner").
RUN_PROCESS = os.environ.get("SENSEI_RUN_PROCESS", "").strip()
# Production database that should never be edited by hand.
PROD_DB = os.environ.get("SENSEI_PROD_DB", "production.db").strip()

# ---------------------------------------------------------------------------
# Logging - file only, never stdout (hook performance requirement)
# ---------------------------------------------------------------------------
STATE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(ACTIVITY_LOG),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("activity_tracker")

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------
HARSH_PATTERNS: list[dict[str, Any]] = [
    {
        "id": "push_during_run",
        "severity": "harsh",
        "check": lambda tool, cmd, fp, cwd: (
            tool == "Bash"
            and cmd is not None
            and "git push" in cmd
            and "--force" not in cmd
            and _long_running_job_active()
        ),
        "detail": "git push while a long-running job is active - session collision possible!",
    },
    {
        "id": "force_push_master",
        "severity": "harsh",
        "check": lambda tool, cmd, fp, cwd: (
            tool == "Bash"
            and cmd is not None
            and "git push" in cmd
            and "--force" in cmd
            and ("master" in cmd or "main" in cmd)
        ),
        "detail": "git push --force onto the main branch - data-loss risk!",
    },
    {
        "id": "server_dir_clone",
        "severity": "warn",
        "check": lambda tool, cmd, fp, cwd: (
            tool == "Bash" and cmd is not None and "scp -r" in cmd and "@" in cmd
        ),
        "detail": "scp -r against a remote host - a whole directory overwritten?",
    },
    {
        "id": "manual_db_edit_prod",
        "severity": "harsh",
        "check": lambda tool, cmd, fp, cwd: (
            tool in ("Edit", "Write")
            and fp is not None
            and bool(PROD_DB)
            and PROD_DB in fp
        ),
        "detail": "direct file edit on the production database - changed by hand!",
    },
]


def _long_running_job_active() -> bool:
    """Checks whether the configured long-running job is running (pgrep, then tasklist).

    Returns False when SENSEI_RUN_PROCESS is not configured.
    """
    if not RUN_PROCESS:
        return False
    try:
        import subprocess

        result = subprocess.run(
            ["pgrep", "-f", RUN_PROCESS],
            capture_output=True,
            timeout=2,
        )
        return result.returncode == 0
    except Exception:
        pass
    try:
        import subprocess

        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return RUN_PROCESS in result.stdout
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Atomic file writes (crash-safe via .tmp + os.replace)
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, data: Any) -> None:
    """Writes JSON atomically via a .tmp file plus os.replace."""
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:
        log.error("atomic_write failed: %s - %s", path, exc)
        tmp.unlink(missing_ok=True)


def _load_json(path: Path, default: Any) -> Any:
    """Loads a JSON file, returning default when it is missing or corrupt."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _infer_action_type(
    tool_name: str,
    command: str | None,
    file_path: str | None,
) -> str:
    """Derives a readable action type from the tool plus its command."""
    if tool_name == "Bash" and command:
        if "git push" in command:
            return "push"
        if "git commit" in command:
            return "commit"
        if "git pull" in command or "git fetch" in command:
            return "pull"
        if "pytest" in command or "python -m test" in command:
            return "test"
        if "ssh" in command or "scp" in command:
            return "deploy"
        if "docker" in command:
            return "docker"
        return "bash"
    if tool_name in ("Edit", "Write"):
        return "edit"
    if tool_name == "Read":
        return "read"
    return "other"


def _project_hash(cwd: str) -> str:
    """SHA-256 of the absolute cwd, first 16 characters - an idempotent project key."""
    return hashlib.sha256(cwd.encode()).hexdigest()[:16]


def _update_last_activity(tool_name: str, action_type: str, cwd: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _atomic_write(
        LAST_ACT,
        {
            "timestamp": now,
            "project_path": cwd,
            "tool_name": tool_name,
            "action_type": action_type,
        },
    )


def _increment_pattern(proj_hash: str, pattern_id: str) -> int:
    """Increments the counter for pattern_id and returns the new count."""
    data: dict = _load_json(PATTERNS, {})
    proj = data.setdefault(proj_hash, {})
    proj[pattern_id] = proj.get(pattern_id, 0) + 1
    _atomic_write(PATTERNS, data)
    return proj[pattern_id]


def _add_to_inbox(pattern_id: str, severity: str, detail: str) -> None:
    """Appends a trigger entry to inbox.json (for the next sensei invocation)."""
    inbox: list = _load_json(INBOX, [])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inbox.append(
        {
            "ts": now,
            "pattern": pattern_id,
            "severity": severity,
            "detail": detail,
        }
    )
    # Cap the inbox at 50 entries
    if len(inbox) > 50:
        inbox = inbox[-50:]
    _atomic_write(INBOX, inbox)


def process_hook(payload: dict) -> None:
    """Processes one hook payload.

    Args:
        payload: {tool_name, tool_input: {command?, file_path?}, cwd}
    """
    tool_name: str = payload.get("tool_name", "")
    tool_input: dict = payload.get("tool_input", {})
    cwd: str = payload.get("cwd", str(Path.home()))

    command: str | None = tool_input.get("command")
    file_path: str | None = tool_input.get("file_path")

    action_type = _infer_action_type(tool_name, command, file_path)
    proj_hash = _project_hash(cwd)

    _update_last_activity(tool_name, action_type, cwd)
    log.info("tool=%s action=%s proj=%s", tool_name, action_type, proj_hash)

    for pattern in HARSH_PATTERNS:
        try:
            triggered: bool = pattern["check"](tool_name, command, file_path, cwd)
        except Exception as exc:
            log.warning("pattern check failed: %s - %s", pattern["id"], exc)
            triggered = False

        if triggered:
            pid = pattern["id"]
            severity = pattern["severity"]
            detail = pattern["detail"]
            count = _increment_pattern(proj_hash, pid)
            _add_to_inbox(pid, severity, detail)
            log.warning(
                "PATTERN [%s] severity=%s count=%d detail=%s",
                pid,
                severity,
                count,
                detail,
            )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Reads stdin as JSON and processes the hook payload. Never crashes."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            log.info("no stdin input - exiting silently")
            return
        payload = json.loads(raw)
        process_hook(payload)
    except json.JSONDecodeError as exc:
        log.error("invalid JSON on stdin: %s", exc)
    except Exception as exc:
        log.error("unexpected error: %s", exc)
    # implicit exit 0 - a hook must never break the Claude session


if __name__ == "__main__":
    main()
