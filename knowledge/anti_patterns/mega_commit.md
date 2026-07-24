---
title: Mega-commit (several days in one commit)
tags: [anti-pattern, git, commits, traceability]
severity: warn
applies_to: [any_git_project]
---
# Mega-Commit

**Pattern:** Squeezing 3-7 days of work into a single commit — no traceability, no rollback possible.

**Yoda warning:** "Everything into one pot you throw — and when it burns, you know not what it was, mhm."

**Fix/Recommendation:** Commit after every completed unit (function, chain, bug fix). Convention: `feat/fix/chore + short description`. Max 2-3h between commits. For longer work: WIP commits with a `wip:` prefix are allowed.

**Pareto:** Small commits cost 30s extra. A mega-commit rollback costs 1-3h and is often incomplete.
