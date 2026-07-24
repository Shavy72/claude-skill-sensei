---
title: Cloning a server directory locally via scp -r
tags: [anti-pattern, deployment, file-management, server]
severity: warn
applies_to: [any_vps_project, any_server_based_deployment]
---
# Cloning a Server Directory Locally via scp

**Pattern:** `scp -r server:/opt/app ./` to grab files — drags along logs, DBs, locks, and binary junk.

**Yoda warning:** "The whole cabinet you pack into the suitcase — but one key only, that you need, hmm."

**Fix/Recommendation:** Only targeted files via `scp server:/opt/app/specific_file.py ./`. For code sync: git is the right way — `git pull` on the server, not a local mirror. DB snapshots explicitly via `sqlite3 .dump`.

**Pareto:** A targeted transfer saves 90% of transfer time and prevents accidentally overwriting local files.
