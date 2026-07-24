---
title: git push --force onto master
tags: [anti-pattern, git, destructive, safety]
severity: harsh
applies_to: [any_git_project_with_team_or_ci]
---
# Force-Push Onto master

**Pattern:** `git push --force origin master` — overwrites history, destroys others' work, breaks CI.

**Yoda anger:** "Crippled this is. The history you erase — what others built, gone it is. No going back there is, mhm."

**Fix/Recommendation:** Never `--force` on master/main. On merge conflict: `git pull --rebase` then a normal push. On a wrong commit: `git revert` instead of rewriting history. If truly necessary: set a branch backup tag first.

**Pareto:** `git revert` costs 2min. Force-push disaster recovery costs hours and destroys trust.
