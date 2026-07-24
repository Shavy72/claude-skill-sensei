# Sensei — a Yoda-styled coding mentor for Claude Code

A Claude Code skill that turns Claude into a blunt but constructive mentor: it reviews your
working habits instead of your syntax, asks *why* you are building something before it helps
you build it, and boils every review down to at most three action items with a Pareto
justification.

It talks like Master Yoda. Verb at the end of the sentence, "hmm" as a breath word, "my
student" as the address. The persona is a delivery vehicle — every reprimand still has to
carry a factual reason and a concrete fix.

## What it does

- **Anti-pattern detection** — a knowledge base of 10 anti-patterns (force-push onto main,
  mega commits, hand-editing a production database, pushing while a long-running job is
  active, building a feature with no stated goal, ...) and 10 counter-workflows.
  Every finding cites the knowledge-base file so you can read up on it.
- **5-Whys onboarding** — when it meets an unknown project it asks five "why" questions
  before it gives any advice, then stores the resulting *why chain* so later sessions can
  check whether today's work still serves the stated goal.
- **Pareto triage** — at most three action items per audit, each with ROI and effort, ranked
  against your primary goal. Items that would distract from the goal are named as such.
- **Mood escalation** — wise by default; stern the second time the same anti-pattern shows
  up; angry the third time. Proud when you get a workflow right.
- **Terminal rendering** — an ANSI/ASCII Yoda with a speech bubble (`runtime/yoda_console.py`),
  in three sizes: MINI (one line), NORMAL (face + items), FULL (audit with a Pareto score bar).
- **Idle triggers** (optional) — a SessionStart hook that greets you after 4h, runs a full
  audit after 10h and a re-onboarding after 72h of inactivity.

## Repository layout

```
SKILL.md                      the skill itself (this is what Claude reads)
triggers.yaml                 modes, inline triggers, thresholds, quiet mode
personas/yoda.md              ASCII art, colour codes, language rules
knowledge/anti_patterns/*.md  10 anti-patterns with fix + Pareto reasoning
knowledge/workflows/*.md      10 counter-workflows to adopt instead
runtime/                      optional Python helpers (renderer, hooks, 5-Whys engine)
mcp/                          optional MCP server for persistent cross-session state
```

## Install (skill only)

The skill works on its own — markdown and YAML, no dependencies:

```bash
git clone https://github.com/Shavy72/claude-skill-sensei ~/.claude/skills/sensei
```

Restart Claude Code. Ask for it by name ("sensei", "run a sensei audit", "review my habits")
or let it trigger itself from a hook (below).

Everything past this point is optional. The skill degrades gracefully: no runtime, no MCP
server, no vault — it still works, it just keeps less state between sessions.

## Optional: the Python runtime

`runtime/` holds the terminal renderer, the two hook scripts and the 5-Whys engine.
Requires Python 3.10+, no third-party packages.

Two ways to wire it up — pick one:

**A. Copy into the default location** (what the docs assume):

```bash
mkdir -p ~/.claude/sensei
cp runtime/*.py ~/.claude/sensei/
python ~/.claude/sensei/yoda_console.py demo   # smoke test: you should see a green Yoda
```

**B. Point `SENSEI_HOME` at the cloned runtime directory** instead of copying:

```bash
export SENSEI_HOME="$HOME/.claude/skills/sensei/runtime"
```

`SENSEI_HOME` is where the scripts read and write their state (`state/`, `projects/`).
`SENSEI_SKILL_DIR` (default `~/.claude/skills/sensei`) is where they look for `triggers.yaml`.

### Hooks (optional)

Add to `~/.claude/settings.json` to get idle detection and automatic pattern counting.
Adjust the paths if you chose option B:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "python ~/.claude/sensei/idle_check.py" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash|Edit|Write",
        "hooks": [
          { "type": "command", "command": "python ~/.claude/sensei/activity_tracker.py" }
        ]
      }
    ]
  }
}
```

Both scripts are written to never fail loudly: they log to `<SENSEI_HOME>/state/*.log` and
always exit 0, so a broken hook can never break your session.

### Runtime environment variables

| Variable | Default | Meaning |
|---|---|---|
| `SENSEI_HOME` | `~/.claude/sensei` | runtime directory (state, projects, scripts) |
| `SENSEI_SKILL_DIR` | `~/.claude/skills/sensei` | where `triggers.yaml` lives |
| `SENSEI_RUN_PROCESS` | _(empty)_ | process name of your long-running job; unset means the "push during an active run" check stays off |
| `SENSEI_PROD_DB` | `production.db` | filename that must never be hand-edited |
| `OBSIDIAN_VAULT` | _(empty)_ | optional vault path; why chains get mirrored there as markdown |

## Optional: the MCP server

`mcp/` contains `sensei-mcp`, a small stdio MCP server that keeps the state in SQLite so it
survives across sessions: activity timestamps, project profiles, pattern counters, why chains
and an audit log.

```bash
pip install ./mcp
```

Then register it in `~/.claude.json` (see `mcp/examples/register_mcp.json`):

```json
{
  "mcpServers": {
    "sensei": {
      "command": "sensei-mcp",
      "args": [],
      "env": {
        "SENSEI_DB_PATH": "/path/to/sensei.db",
        "OBSIDIAN_VAULT": "/path/to/your/obsidian-vault"
      }
    }
  }
}
```

`SENSEI_DB_PATH` defaults to `~/.claude/sensei/state/sensei.db` and the database is created on
first start. Tools exposed: `record_activity`, `get_idle_seconds`, `get_project_profile`,
`upsert_project_profile`, `record_pattern`, `get_patterns`, `record_why_chain`, `get_why_chain`.
Details in [mcp/README.md](mcp/README.md).

## Graceful degradation

As stated in `SKILL.md`, every optional component is optional:

| Missing | Consequence |
|---|---|
| MCP server | falls back to file state under `<SENSEI_HOME>/state/` |
| memory MCP (e.g. claude-mem) | no long-term recall of past sessions, everything else works |
| `OBSIDIAN_VAULT` | no markdown mirror of the why chains |
| the whole `runtime/` | no ASCII rendering and no idle triggers; the skill still audits when you ask it to |

## Customising it

- **Knowledge base:** the files under `knowledge/` are plain markdown with YAML frontmatter
  (`title`, `tags`, `severity`, `applies_to`). Drop in your own anti-patterns and workflows —
  the skill matches against whatever is in those folders.
- **Triggers and thresholds:** `triggers.yaml` (idle thresholds in seconds, mode escalation,
  cost caps, quiet mode).
- **Voice:** `personas/yoda.md`. Replace the ASCII art and the language rules if you want a
  different mentor — the skill logic does not care who is talking.

## Licence

MIT — see [LICENSE](LICENSE).
