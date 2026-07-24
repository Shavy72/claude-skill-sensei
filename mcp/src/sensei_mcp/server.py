"""Sensei MCP Server — 8 tools for persistent cross-session state.

Entry point: sensei-mcp (via pyproject.toml [project.scripts]).
Separation: no SQL here — everything via db.py. Storage bridges via storage_adapters.py.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from sensei_mcp import __version__
from sensei_mcp.db import (
    get_idle_seconds,
    get_patterns,
    get_project_profile,
    get_why_chain,
    init_db,
    record_activity,
    record_pattern,
    record_why_chain,
    upsert_project_profile,
)
from sensei_mcp.storage_adapters import ClaudeMemAdapter, ObsidianAdapter

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------


def _setup_logging() -> None:
    """Configures a RotatingFileHandler writing to ~/.claude/sensei/state/server.log."""
    log_dir = Path.home() / ".claude" / "sensei" / "state"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "server.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.addHandler(handler)


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server instance + adapters
# ---------------------------------------------------------------------------

_server = Server("sensei-mcp")
_claude_mem = ClaudeMemAdapter()
_obsidian = ObsidianAdapter()


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


@_server.list_tools()
async def list_tools() -> list[Tool]:
    """Returns all 8 Sensei tools."""
    return [
        Tool(
            name="record_activity",
            description=(
                "Records an activity (project_path, action_type, payload). "
                "Bumps last_activity. Triggers an Obsidian audit entry if OBSIDIAN_VAULT is set."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                    },
                    "action_type": {
                        "type": "string",
                        "description": "Action label (e.g. file_edit, test_run, session_start)",
                    },
                    "payload": {"description": "Optional JSON-serializable payload"},
                },
                "required": ["project_path", "action_type"],
            },
        ),
        Tool(
            name="get_idle_seconds",
            description="Returns seconds since the last recorded activity (system-wide).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_project_profile",
            description=(
                "Loads the stored profile for a project path. "
                "Returns null if no entry exists."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                    },
                },
                "required": ["project_path"],
            },
        ),
        Tool(
            name="upsert_project_profile",
            description="Writes or updates a project's profile (profile_yaml, stage, stack).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "profile_yaml": {
                        "type": "string",
                        "description": "YAML string with profile content",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Development stage (e.g. warmup, production, legacy)",
                    },
                    "stack": {
                        "type": "string",
                        "description": "Tech stack as free text",
                    },
                },
                "required": ["project_path", "profile_yaml", "stage", "stack"],
            },
        ),
        Tool(
            name="record_pattern",
            description="Increments the counter for a pattern (UPSERT). Returns the new counter value.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "pattern_id": {
                        "type": "string",
                        "description": "Unique pattern name (e.g. missing-type-hints)",
                    },
                },
                "required": ["project", "pattern_id"],
            },
        ),
        Tool(
            name="get_patterns",
            description="Returns all patterns of a project, sorted by counter DESC.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="record_why_chain",
            description=(
                "Stores a why-chain: list of {depth: int, question: str, answer: str} dicts. "
                "All entries get the same captured_at timestamp (batch)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "answers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "depth": {
                                    "type": "integer",
                                    "description": "Why depth (1=first why)",
                                },
                                "question": {"type": "string"},
                                "answer": {"type": "string"},
                            },
                            "required": ["depth", "question", "answer"],
                        },
                    },
                },
                "required": ["project", "answers"],
            },
        ),
        Tool(
            name="get_why_chain",
            description=(
                "Loads the most recent why-chain of a project (latest captured_at batch), "
                "sorted by depth ASC."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                },
                "required": ["project"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------


@_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatches every incoming tool call to the matching handler function.

    Args:
        name:      Tool name (must be defined in list_tools()).
        arguments: Tool arguments as a dict.

    Returns:
        List with a single TextContent element (JSON-serialized result).
    """
    logger.info("Tool call: name=%s args=%s", name, arguments)

    try:
        result = await _dispatch(name, arguments)
    except Exception as exc:
        logger.exception("Tool call error: name=%s", name)
        return [
            TextContent(
                type="text", text=json.dumps({"error": str(exc)}, ensure_ascii=False)
            )
        ]

    return [
        TextContent(
            type="text", text=json.dumps(result, ensure_ascii=False, default=str)
        )
    ]


async def _dispatch(name: str, args: dict[str, Any]) -> Any:
    """Internal dispatcher — returns a Python object (serialized in call_tool).

    Args:
        name: Tool name.
        args: Tool arguments.

    Returns:
        JSON-serializable Python object.

    Raises:
        ValueError: If the tool name is unknown.
    """
    if name == "record_activity":
        record_activity(
            project_path=args["project_path"],
            action_type=args["action_type"],
            payload=args.get("payload"),
        )
        _obsidian.write_audit(
            project=args["project_path"],
            severity="INFO",
            message=f"Activity: {args['action_type']}",
        )
        return {"status": "ok"}

    if name == "get_idle_seconds":
        return {"idle_seconds": get_idle_seconds()}

    if name == "get_project_profile":
        return get_project_profile(args["project_path"])

    if name == "upsert_project_profile":
        upsert_project_profile(
            project_path=args["project_path"],
            profile_yaml=args["profile_yaml"],
            stage=args["stage"],
            stack=args["stack"],
        )
        return {"status": "ok"}

    if name == "record_pattern":
        counter = record_pattern(
            project=args["project"],
            pattern_id=args["pattern_id"],
        )
        return {"counter": counter}

    if name == "get_patterns":
        return get_patterns(args["project"])

    if name == "record_why_chain":
        record_why_chain(
            project=args["project"],
            answers=args["answers"],
        )
        return {"status": "ok", "entries": len(args["answers"])}

    if name == "get_why_chain":
        return get_why_chain(args["project"])

    raise ValueError(f"Unknown tool: {name!r}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Initializes logging + DB and starts the MCP stdio server."""
    _setup_logging()
    logger.info("Sensei MCP v%s starting.", __version__)
    init_db()

    import asyncio

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await _server.run(
                read_stream,
                write_stream,
                _server.create_initialization_options(),
            )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
