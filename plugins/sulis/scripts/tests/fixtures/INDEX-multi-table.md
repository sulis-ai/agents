# Work Package Index — kinds-and-tools

> **Slice-1 ship-first set:** A representative downstream INDEX shape
> that has a `## Primitive Summary` table BEFORE the canonical
> `## Work Packages` table. The Primitive Summary's first column is
> also "ID" (the primitive ID), which is the cause of Bug 2 —
> `_find_wp_table` greedily matches the first `| ID |` header.

## Orchestrator Config

max_parallel: 3

## Primitive Summary

| ID | Group | Count |
|---|---|---|
| EXPAND | Create | 17 |
| REORGANISE | Move | 3 |
| REINFORCE | Test | 15 |

## Work Packages

| ID | Title | Primitive | Status | Depends | Blocks | Token | TDD § |
|---|---|---|---|---|---|---|---|
| WP-001 | First | Create | done | — | WP-002 | 5k | 2.1 |
| WP-002 | Second | Extend | in_progress | WP-001 | — | 4k | 2.2 |
| WP-CHAR-01 | Characterisation suite | Test | pending | WP-001 | WP-MIG-1 | 3k | 5.4 |
| WP-MIG-1 | Move engine primitives | Move | pending | WP-CHAR-01 | — | 9k/5k | — |
