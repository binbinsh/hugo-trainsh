+++
title = "Data Migration Lessons"
date = "2021-11-03"
draft = false
tags = ["data", "migration", "lessons"]
+++

## Plan
- Inventory sources and consumers.
- Define cutover criteria and rollback.

## Do
- Backfill with idempotent jobs.
- Dual-write during the window.

## Learn
- Shadow traffic reveals schema gaps.
- Observability per table prevents surprises.
