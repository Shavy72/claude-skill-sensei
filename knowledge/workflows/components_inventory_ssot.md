---
title: Components inventory as single source of truth
tags: [workflow, documentation, ssot, inventory]
severity: praise
applies_to: [any_multi_component_system, automation_pipeline]
---
# Components Inventory SSOT

**Pattern:** A central inventory file lists all building blocks with active/legacy/dropped status. Every session reads it first.

**Yoda praise:** "One source of truth — it prevents two hands from carrying the same stone to two places, hmm."

**Fix/Recommendation:** Update `components_inventory.json` after every building-block change: mark the old version `status: legacy`, the new one `active` with date + commit hash. Never work from memory — always ask the inventory.

**Pareto:** 3min of update discipline prevents ghost-code use and accidental legacy repairs.
