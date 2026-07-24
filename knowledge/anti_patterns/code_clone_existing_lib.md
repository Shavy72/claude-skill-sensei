---
title: Building yourself what a library already does
tags: [anti-pattern, reuse, library, not-invented-here]
severity: advice
applies_to: [any_development_project]
---
# Not-Invented-Here Self-Build

**Pattern:** Implementing a function yourself that already exists in stdlib, existing deps, or repo code.

**Yoda hint:** "Built already it was — by others, better tested. Find it you must, hmm."

**Fix/Recommendation:** Library-first search before every new build (see workflows/library_first_search.md). When in doubt: check the package docs. Build it yourself only when: the lib is too large, there's a license problem, or the customization would exceed 50% of the lib's code.

**Pareto:** A 5min search saves on average 45min of implementation plus the ongoing maintenance burden of the self-built solution.
