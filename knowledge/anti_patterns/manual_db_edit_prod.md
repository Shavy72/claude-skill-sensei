---
title: Directly editing the production database
tags: [anti-pattern, database, safety, production]
severity: harsh
applies_to: [any_sqlite_project, any_production_database]
---
# Manual Prod-DB Editing

**Pattern:** Running `sqlite3 production.db` directly on the prod server and changing data by hand — no audit, no rollback.

**Yoda anger:** "The living database you touch with bare hands — dangerous this is, mhm. One typo, and gone the records are."

**Fix/Recommendation:** Always: backup first (`sqlite3 production.db .dump > backup_.sql`). Changes via API endpoint or migration script — never raw SQL edits without a wrapper. For emergency edits: backup mandatory + audit-log entry.

**Pareto:** A 30s backup command prevents a 100% data-loss risk. No backup = Russian roulette.
