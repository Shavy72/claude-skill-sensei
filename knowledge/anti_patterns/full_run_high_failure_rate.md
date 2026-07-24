---
title: Full run at more than 80% failure rate
tags: [anti-pattern, testing, debugging, failure-rate]
severity: harsh
applies_to: [any_automation_system, rpa_workflow, adb_automation]
---
# Full Run at High Failure Rate

**Pattern:** Starting a full-day run despite a >80% failure rate — costs time, yields no new information.

**Yoda anger:** "Foolish this is, yes! Eighty times running into the wall — and the wall, it does not move, hmm. Stop you must."

**Fix/Recommendation:** At >80% failure rate: stop immediately. Isolated smoke test of the failing unit. Only once the isolated test is green: escalate to the wrap test. Full run only once the wrap test shows <20% failure rate. Always check the failure rate after the first third of a run.

**Pareto:** An early abort saves 66% of runtime and, through isolation, delivers 3x better debug info.
