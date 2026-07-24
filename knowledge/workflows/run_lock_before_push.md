---
title: Run lock before server push
tags: [workflow, safety, concurrency, server]
severity: praise
applies_to: [any_server_with_running_processes, any_deployment_workflow]
---
# Run Lock Before Server Push

**Pattern:** Before every deploy/push, check whether server processes are active. Never deploy blindly.

**Yoda praise:** "Check first, then act — this is the way, my student. The running process you kill otherwise, mid-run."

**Fix/Recommendation:** Run `pgrep -f <your-long-running-job>` before push. On a hit: wait or stop it in a coordinated way. Deploy script: build the lock check in as the first step (`if pgrep -f <your-long-running-job> > /dev/null; then echo "BLOCKED"; exit 1; fi`).

**Pareto:** A 3-second check prevents potentially corrupted DB writes and aborted worker sessions.
