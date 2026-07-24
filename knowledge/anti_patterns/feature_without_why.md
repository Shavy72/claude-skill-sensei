---
title: Building a feature without a goal justification
tags: [anti-pattern, planning, clarity, waste]
severity: advice
applies_to: [any_development_project, any_feature_planning]
---
# Feature Without a Why

**Pattern:** Jumping straight into implementation without asking: which problem does this solve? Which user benefits?

**Yoda hint:** "Building without a goal — walking without direction, this is, my student. Exhausted you arrive, but where?"

**Fix/Recommendation:** Before every feature: write one sentence — 'This feature solves [problem X] for [who Y], measurable by [Z]'. If that sentence cannot be formulated: do not build the feature. Walk through the 5-Whys (see workflows/why_chain_5_whys.md).

**Pareto:** A 5min clarity check prevents 4-8h of implementing features nobody needs or that get solved wrong.
