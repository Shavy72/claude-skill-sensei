---
title: Local-first development
tags: [workflow, dev-loop, pareto, docker]
severity: praise
applies_to: [any_project_with_docker, any_project_with_remote_deploy]
---
# Local-First Development

**Pattern:** A local Docker Compose instance mirrors the server exactly. Every iteration without a push cycle.

**Yoda praise:** "Wisely you work, hmm. Thirty minutes you save per iteration — many days in the month, that adds up to."

**Fix/Recommendation:** `docker-compose.yml` with the same image version as prod. Hot-reload via volume mount (`./:/app`). Inject env vars from `.env.local` — never touch the production `.env` file.

**Pareto:** Effort: 30min setup, once · Benefit: ~3min/iter × 20 iter/day = 1h saved daily. ROI positive from day 1.
