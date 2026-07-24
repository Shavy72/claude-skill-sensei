# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-07-24

Initial public release of the sensei coding-mentor skill.

- Skill (`SKILL.md`) with anti-pattern detection, 5-Whys onboarding, Pareto triage and mood
  escalation.
- Knowledge base: 10 anti-patterns (`knowledge/anti_patterns/`) and 10 counter-workflows
  (`knowledge/workflows/`).
- Optional Python runtime (`runtime/`): terminal renderer, idle/activity hooks, 5-Whys engine.
- Optional MCP server (`mcp/`) for persistent cross-session state via SQLite.
