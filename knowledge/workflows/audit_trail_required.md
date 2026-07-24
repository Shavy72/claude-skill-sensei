---
title: Audit trail required before destructive action
tags: [workflow, safety, logging, audit]
severity: praise
applies_to: [any_project_with_destructive_operations, db_management, file_operations]
---
# Audit Trail Required Before Destructive Action

**Pattern:** Every destructive action (delete, reset, truncate, force-push) is logged beforehand — timestamp, what, why, who.

**Yoda praise:** "Evidence you leave behind, when you act — for tomorrow you ask yourself: what have I done, hmm?"

**Fix/Recommendation:** Before every `DELETE FROM`, `git push --force`, `truncate`, `rm -rf`: write one log line (`audit.log`: ISO timestamp + action + justification). For DBs: snapshot beforehand. For git: branch backup tag.

**Pareto:** 10 seconds of logging per action gives 100% traceability. A rollback without a log costs hours.
