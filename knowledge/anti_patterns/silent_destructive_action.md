---
title: Destructive action without user confirmation
tags: [anti-pattern, safety, ux, destructive]
severity: harsh
applies_to: [any_automated_system, any_cli_tool, any_dashboard]
---
# Silent Destructive Action

**Pattern:** Running delete, reset, truncate, or force-stop without user confirmation or a visible warning.

**Yoda anger:** "In silence you destroy — and the user? He knows it not, until too late it is, hmm. That I do not forgive."

**Fix/Recommendation:** Every destructive action needs: 1. An explicit warning with the consequence. 2. A confirm step (CLI: 'yes/no', API: `confirm=true` parameter). 3. An audit-log entry after execution. No dry-run = no execution on first introduction runs.

**Pareto:** A confirm dialog costs 3s. A silent-delete disaster costs hours of recovery and permanently damages trust.
