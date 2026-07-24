# Sensei MCP

Persistent cross-session state MCP server for an AI coding mentor (Yoda persona).
Keeps SQLite state alive across Claude sessions: activity, project profiles,
patterns, why-chains, anger levels, audit log.

## Installation

```bash
cd /path/to/sensei-mcp
pip install -e .
```

## MCP Registration in Claude

Entry in `~/.claude.json` under `mcpServers` (see `examples/register_mcp.json`):

```json
{
  "mcpServers": {
    "sensei": {
      "command": "sensei-mcp",
      "args": []
    }
  }
}
```

## Env Vars

| Variable | Default | Description |
|---|---|---|
| `SENSEI_DB_PATH` | `~/.claude/sensei/state/sensei.db` | Path to the SQLite DB |
| `OBSIDIAN_VAULT` | _(empty)_ | Path to the Obsidian vault for audit export |

## Storage Bridges

### claude-mem Bridge
`ClaudeMemAdapter` is a no-op stub. Reason: claude-mem is a separate MCP server
addressed via its own tool calls — a direct Python import is not possible.
The adapter logs hints about which claude-mem tool calls the caller should make itself.

### Obsidian Bridge
`ObsidianAdapter` writes audit entries to:
```
$OBSIDIAN_VAULT/projects/sensei/audits/YYYY-MM-DD.md
```
If `OBSIDIAN_VAULT` is not set, the adapter is disabled (no error).

## Database

SQLite at `~/.claude/sensei/state/sensei.db` — created automatically on first start.

### Tables

- `last_activity` — last action per session (project_path, action_type, payload, ts)
- `project_profiles` — profile per repo (repo_hash, profile_yaml, stage, stack, updated_at)
- `patterns` — detected patterns (project, pattern_id, counter, last_seen, status)
- `audit_log` — audit trail (ts, project, severity, message, action_taken)
- `anger_levels` — anger counter per pattern+project
- `why_answers` — why-chain answers (project, depth, question, answer, captured_at)

## License

MIT — see [LICENSE](LICENSE)
