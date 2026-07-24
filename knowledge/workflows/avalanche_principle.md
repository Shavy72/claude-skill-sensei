---
title: Avalanche principle (cross-stage bug propagation)
tags: [workflow, bug-fix, propagation, cross-day]
severity: praise
applies_to: [multi_stage_automation, day_by_day_warmup, sequential_pipeline]
---
# Avalanche Principle

**Pattern:** A bug fix in a central building block propagates automatically to every stage that uses it — when the fix sits in the right place.

**Yoda praise:** "Fix once, heal everywhere — wisdom this is, mhm. Not solve the same error five times in five places."

**Fix/Recommendation:** Before every fix: check `components_inventory.json`, read `tags_used_in: [S1, S3, S7]`. Place the fix in the central chain file, not in the per-stage wrapper. Set the coverage line in the bugfix journal.

**Pareto:** A 5min inventory check saves 5x the fix effort when a building block is active across many stages.
