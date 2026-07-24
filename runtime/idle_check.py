"""idle_check.py - Sensei SessionStart hook.

Caller: SessionStart hook in ~/.claude/settings.json (payload on stdin).
Schema:
  Input (stdin): {hook_event_name: str, source: str, cwd: str, session_id: str}
  Reads:  <SENSEI_HOME>/state/last_activity.json  -> {timestamp: ISO, ...}
  Reads:  <SENSEI_SKILL_DIR>/triggers.yaml        -> idle_thresholds: {light, full, reonboarding}
  Reads:  <SENSEI_HOME>/state/quiet_until.txt     -> ISO timestamp (optional)
  Writes stdout: hook JSON with additionalContext when a trigger fires
  Logfile: <SENSEI_HOME>/state/idle.log

Environment:
  SENSEI_HOME       override for the runtime directory (default: ~/.claude/sensei)
  SENSEI_SKILL_DIR  override for the skill directory   (default: ~/.claude/skills/sensei)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SENSEI_HOME = Path(
    os.environ.get("SENSEI_HOME") or (Path.home() / ".claude" / "sensei")
)
SKILL_DIR = Path(
    os.environ.get("SENSEI_SKILL_DIR")
    or (Path.home() / ".claude" / "skills" / "sensei")
)
STATE_DIR = SENSEI_HOME / "state"
LAST_ACT = STATE_DIR / "last_activity.json"
TRIGGERS_YML = SKILL_DIR / "triggers.yaml"
QUIET_UNTIL = STATE_DIR / "quiet_until.txt"
PROJECTS_DIR = SENSEI_HOME / "projects"
IDLE_LOG = STATE_DIR / "idle.log"

STATE_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging - file only, never stdout (hook requirement)
# ---------------------------------------------------------------------------
logging.basicConfig(
    filename=str(IDLE_LOG),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("idle_check")

# ---------------------------------------------------------------------------
# Default thresholds (used when triggers.yaml is missing)
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLDS: dict[str, int] = {
    "light": 4 * 3600,  # 4h  -> light greeting
    "full": 10 * 3600,  # 10h -> full audit (NORMAL mode)
    "reonboarding": 72 * 3600,  # 72h -> re-onboarding
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str) -> datetime:
    """Parses an ISO-8601 timestamp (with or without Z) into a UTC-aware datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _load_json(path: Path, default: object) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _load_thresholds() -> dict[str, int]:
    """Loads the thresholds from triggers.yaml (minimal parsing, no yaml dependency)."""
    if not TRIGGERS_YML.exists():
        return DEFAULT_THRESHOLDS
    try:
        thresholds = dict(DEFAULT_THRESHOLDS)
        for line in TRIGGERS_YML.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            for key in ("light", "full", "reonboarding"):
                if line.startswith(f"{key}:"):
                    try:
                        thresholds[key] = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
        return thresholds
    except Exception as exc:
        log.warning("triggers.yaml parse failed: %s - using defaults", exc)
        return DEFAULT_THRESHOLDS


def _is_quiet() -> bool:
    """True when quiet_until.txt points into the future."""
    if not QUIET_UNTIL.exists():
        return False
    try:
        until = _parse_iso(QUIET_UNTIL.read_text(encoding="utf-8").strip())
        return _now_utc() < until
    except Exception:
        return False


def _is_known_project(cwd: str) -> bool:
    """True when a profile.yml already exists for this project."""
    repo_hash = hashlib.sha256(cwd.encode()).hexdigest()[:16]
    return (PROJECTS_DIR / repo_hash / "profile.yml").exists()


def _idle_seconds() -> float | None:
    """Seconds since the last recorded activity. None when there is no data."""
    data = _load_json(LAST_ACT, {})
    if not isinstance(data, dict) or "timestamp" not in data:
        return None
    try:
        last = _parse_iso(data["timestamp"])
        return (_now_utc() - last).total_seconds()
    except Exception:
        return None


def _hook_output(ctx: str) -> str:
    """Builds a valid SessionStart hook JSON payload."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": ctx,
            }
        },
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Trigger texts
# ---------------------------------------------------------------------------


def _trigger_light(idle_h: float) -> str:
    return _hook_output(
        f"Sensei trigger: idle {idle_h:.1f}h. "
        f"Greet the user briefly with a Yoda line via "
        f"{SENSEI_HOME / 'yoda_console.py'} render_mini (mood=wise). "
        "No full audit - one line only."
    )


def _trigger_full(idle_h: float) -> str:
    return _hook_output(
        f"Sensei trigger: idle {idle_h:.1f}h. "
        "Start the sensei skill now in NORMAL mode. "
        f"Load {STATE_DIR / 'inbox.json'} for the active patterns. "
        f"Render via {SENSEI_HOME / 'yoda_console.py'} render_normal."
    )


def _trigger_gross(idle_h: float) -> str:
    return _hook_output(
        f"Sensei trigger: idle {idle_h:.1f}h - a full audit is due. "
        "Start the sensei skill in FULL mode. "
        f"Load the why chain from {PROJECTS_DIR / '<repo_hash>' / 'why_chain.md'}. "
        "Compute the Pareto score and the why alignment. "
        f"Render via {SENSEI_HOME / 'yoda_console.py'} render_gross."
    )


def _trigger_reonboarding(idle_h: float) -> str:
    return _hook_output(
        f"Sensei re-onboarding: idle {idle_h:.1f}h (>= 72h break). "
        "Run the 5-Whys onboarding: "
        f"python {SENSEI_HOME / 'why_engine.py'} start - "
        "ask all five why questions one by one, then store the result. "
        "Render the welcome audit via render_gross."
    )


def _trigger_new_project(cwd: str) -> str:
    return _hook_output(
        f"Sensei onboarding: new project detected ({cwd}). "
        "Run the 5-Whys onboarding: "
        f"python {SENSEI_HOME / 'why_engine.py'} start - "
        "ask all five why questions one by one, store them in profile.yml and the vault. "
        "Greet with render_mini (mood=questioning)."
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """SessionStart hook: reads stdin, decides the trigger mode, writes stdout."""
    try:
        raw = sys.stdin.read()
        payload: dict = json.loads(raw) if raw.strip() else {}
        cwd: str = payload.get("cwd", str(Path.home()))

        # Quiet mode: a SessionStart trigger is always dropped silently
        if _is_quiet():
            log.info("quiet_until active - no trigger")
            return

        # New project -> onboarding regardless of idle time
        if cwd and not _is_known_project(cwd):
            log.info("new project: %s", cwd)
            print(_trigger_new_project(cwd))
            return

        # Compute idle time
        idle = _idle_seconds()
        if idle is None:
            log.info("no last_activity - no trigger")
            return

        thresholds = _load_thresholds()
        idle_h = idle / 3600
        log.info("idle=%.1fh cwd=%s", idle_h, cwd)

        if idle >= thresholds["reonboarding"]:
            print(_trigger_reonboarding(idle_h))
        elif idle >= thresholds["full"]:
            print(_trigger_gross(idle_h))
        elif idle >= thresholds["light"]:
            print(_trigger_light(idle_h))
        else:
            log.info("idle %.1fh below the light threshold - no output", idle_h)

    except Exception as exc:
        # Never crash - the hook must always exit 0
        log.error("idle_check exception: %s", exc)


if __name__ == "__main__":
    main()
