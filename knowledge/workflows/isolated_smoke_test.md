---
title: Isolated smoke test wrap
tags: [workflow, testing, iteration-speed, pareto]
severity: praise
applies_to: [any_rpa_automation, any_chain_based_system, any_adb_workflow]
---
# Isolated Smoke Test Wrap

**Pattern:** Test a single chain/action in isolation inside a minimal wrapper — 3-5 minutes instead of a 40-minute full run.

**Yoda praise:** "Fast you learn, when small you test, mhm. The full run — it shows you not where the fault sits."

**Fix/Recommendation:** Per action, one `test_iso_<action>.py` with minimal setup (1 worker, 1 unit, at most 1 batch). Only once the isolated test is green: build it into the full-day wrapper. Never debug directly inside the production run.

**Pareto:** 20% effort (writing the isolated wrapper) prevents 80% of debugging time on full-run failures. Break-even after the first caught bug.
