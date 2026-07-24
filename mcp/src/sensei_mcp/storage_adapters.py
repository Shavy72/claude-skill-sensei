"""Storage bridges for Sensei MCP.

Two adapters:
- ClaudeMemAdapter: no-op stub (claude-mem is a separate MCP server, no direct import)
- ObsidianAdapter: writes audit markdown to $OBSIDIAN_VAULT/projects/sensei/audits/YYYY-MM-DD.md
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ClaudeMemAdapter
# ---------------------------------------------------------------------------


class ClaudeMemAdapter:
    """No-op stub for claude-mem MCP integration.

    claude-mem runs as a separate MCP server and is reachable only via its
    own tool calls — a direct Python import is not possible. This adapter logs
    hints about which claude-mem tool calls the caller should execute itself.
    """

    def store_memory(self, key: str, value: str, project: str | None = None) -> None:
        """No-op: logs a hint about the required claude-mem tool call.

        Args:
            key:     Memory key (e.g. "last_pattern").
            value:   Value to store.
            project: Optional project context.
        """
        logger.info(
            "[claude-mem STUB] Caller should execute tool call: "
            "mcp__plugin_claude-mem_mcp-search__build_corpus with key=%s project=%s. "
            "Direct Python import not possible — claude-mem is a separate MCP server.",
            key,
            project,
        )

    def search_memory(self, query: str, project: str | None = None) -> list[dict]:
        """No-op: returns an empty list + logs a hint.

        Args:
            query:   Search term.
            project: Optional project filter.

        Returns:
            Always an empty list — real access requires a claude-mem tool call.
        """
        logger.info(
            "[claude-mem STUB] Caller should execute tool call: "
            "mcp__plugin_claude-mem_mcp-search__smart_search with query=%r project=%s.",
            query,
            project,
        )
        return []


# ---------------------------------------------------------------------------
# ObsidianAdapter
# ---------------------------------------------------------------------------


class ObsidianAdapter:
    """Writes audit entries as markdown into the Obsidian vault.

    Target path: $OBSIDIAN_VAULT/projects/sensei/audits/YYYY-MM-DD.md
    If OBSIDIAN_VAULT is not set, the adapter is disabled (no error).
    """

    def __init__(self) -> None:
        vault_env = os.environ.get("OBSIDIAN_VAULT", "").strip()
        self._vault: Path | None = Path(vault_env) if vault_env else None
        if self._vault:
            logger.info("ObsidianAdapter active: vault=%s", self._vault)
        else:
            logger.info("ObsidianAdapter disabled (OBSIDIAN_VAULT not set).")

    @property
    def enabled(self) -> bool:
        """True if OBSIDIAN_VAULT is set and exists."""
        return self._vault is not None and self._vault.exists()

    def _audit_path(self) -> Path:
        """Returns today's audit path (UTC date)."""
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        audit_dir = self._vault / "projects" / "sensei" / "audits"  # type: ignore[operator]
        audit_dir.mkdir(parents=True, exist_ok=True)
        return audit_dir / f"{today}.md"

    def write_audit(
        self,
        project: str,
        severity: str,
        message: str,
        action_taken: str | None = None,
    ) -> None:
        """Appends an audit entry to the day's markdown file.

        Args:
            project:      Project identifier.
            severity:     Log-level string (e.g. "INFO", "WARN", "ERROR").
            message:      Audit message.
            action_taken: Optional description of the countermeasure taken.
        """
        if not self.enabled:
            logger.debug("ObsidianAdapter disabled — audit entry skipped.")
            return

        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            f"\n## [{severity}] {ts}",
            f"**Project:** `{project}`",
            f"**Message:** {message}",
        ]
        if action_taken:
            lines.append(f"**Action taken:** {action_taken}")
        lines.append("")

        audit_path = self._audit_path()
        try:
            with audit_path.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            logger.debug("ObsidianAdapter wrote audit to %s", audit_path)
        except OSError as exc:
            logger.error("ObsidianAdapter: write error %s: %s", audit_path, exc)
