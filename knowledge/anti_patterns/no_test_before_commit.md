---
title: 60 minutes, no verification before commit
tags: [anti-pattern, testing, verification, commit]
severity: warn
applies_to: [any_development_project, automation_system]
---
# No Test Before Commit

**Pattern:** Committing code without prior execution / verification — errors land in history.

**Yoda warning:** "Blindly commit you must not. What untested enters the repo — it returns, but as a bug, mhm."

**Fix/Recommendation:** Mandatory check before every commit: run the function once and see the output. For scripts: run once with test data. For chains: isolated smoke test. Commit message must contain proof: 'tested on worker X, output OK'.

**Pareto:** A 5min test before commit prevents on average 30min of bug hunting after the commit, in 30% of cases.
