---
title: Pushing while a server run is active
tags: [anti-pattern, safety, concurrency, deployment]
severity: warn
applies_to: [any_server_with_running_processes, any_deployment_workflow]
---
# Pushing While a Server Run Is Active

**Pattern:** Deploying or pushing while a long-running automation job is active — leads to a mid-session abort.

**Yoda warning:** "Blindly you act, my student. The moving train you stop mid-bridge — what follows, that you know."

**Fix/Recommendation:** Always run `pgrep -f <your-long-running-job>` before push. Deploy script with a lock guard: `if [ -f tmp/run.lock ]; then exit 1; fi`. In CI/CD: deploy only when no active run-lock exists in the system.

**Pareto:** A 3-second check prevents corrupted DB writes, aborted worker sessions, and race conditions.
