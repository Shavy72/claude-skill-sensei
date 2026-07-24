---
title: Pareto triage by failure rate
tags: [workflow, triage, failure-rate, pareto, testing]
severity: praise
applies_to: [any_automation_system, rpa_workflow, adb_automation]
---
# Pareto Triage by Failure Rate

**Pattern:** Failure rate determines the test strategy. <20%: full run OK. 20-80%: wrap test. >80%: isolated smoke test only.

**Yoda praise:** "The right hammer for the right nail you choose — that shows you understand, my student."

**Fix/Recommendation:** After every run, compute the failure rate: `failed_units / total_units`. >80% stop immediately, isolated debug. 20-80% wrap test with logging. <20% full run with elevated log level. Never run a full run at >80%.

**Pareto:** Choosing the right test tier saves 60-80% of debugging runtime without losing information.
