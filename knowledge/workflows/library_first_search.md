---
title: Library-first search before a new build
tags: [workflow, reuse, library, search-first]
severity: praise
applies_to: [any_development_project, any_coding_task]
---
# Library-First Search

**Pattern:** Before every new build: spend 5 minutes searching whether a solution already exists — locally, in the repo, in known libraries.

**Yoda praise:** "The wheel you reinvent not — too clever for that you are, hmm. Search first, then build."

**Fix/Recommendation:** Order: 1. `grep -r function_name ./automation/` 2. Check `components_inventory.json` 3. Check Python stdlib / known deps. Build it yourself only after 3 misses. Link what you found immediately in the inventory.

**Pareto:** A 5min search saves on average 45min of build effort in 40% of cases (every 3rd function already exists).
