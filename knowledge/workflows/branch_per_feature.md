---
title: One branch per day/feature
tags: [workflow, git, branching, pareto]
severity: praise
applies_to: [any_git_project, multi_day_feature_work]
---
# One Branch per Day/Feature

**Pattern:** A dedicated git branch for every day or every feature. No mega-commit at the end of the week.

**Yoda praise:** "Cleanly you work, yes. When something breaks — roll back you can, without losing everything, hmm."

**Fix/Recommendation:** `git checkout -b feat/day3-worker-chain` at the start of every feature day. Small commits during the work. Merge via PR after verification — never push directly to master.

**Pareto:** 2min of branch discipline daily saves on average 45min of rollback pain per 1 broken merge/week.
