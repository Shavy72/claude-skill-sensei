---
title: Goal clarity through 5-Whys
tags: [workflow, clarity, goal, 5-whys]
severity: praise
applies_to: [any_feature_planning, architecture_decision, debugging]
---
# 5-Whys Goal Clarity

**Pattern:** Before every feature/fix: ask 'why?' 5 times until the real goal is clear — not just solving the described symptom.

**Yoda hint:** "The symptom you treat — but the cause? It still whispers, mhm. Ask five times you must."

**Fix/Recommendation:** For every new task: write out 3-5 why-steps. If the answer at why-3 already suffices as the fix — discard the earlier implementation idea. Name the goal in the first sentence of the commit message.

**Pareto:** 10min of goal clarification prevents 2-4h of implementing the wrong solution — especially for bugs with an unclear root cause.
