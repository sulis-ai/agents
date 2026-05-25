# Software Requirements Document: Auto Codebase Mapping

**Version:** 1.0.0
**Date:** 2026-03-13
**Status:** Draft
**Author:** Iain (facilitated by Requirements Analyst)

---

## 1. Introduction

### 1.1 Purpose

Specifies the automatic background codebase mapping behaviour for the SRD
requirements-analyst agent. When the agent starts a facilitation session, it should
automatically map the existing codebase to ground its questions in what already exists
— without requiring the user to ask for it.

### 1.2 Scope

**In scope:**
- Automatic trigger of codebase mapping at agent/session start
- Staleness detection to avoid redundant scans
- Greenfield project detection and silent skip
- Overlay of codebase context into the facilitation conversation
- Progressive disclosure depth model (broad map → targeted deep dives)

**Out of scope:**
- Changes to what the mapper scans (the mapping process itself is unchanged)
- Changes to the CODEBASE_INDEX.json output format
- Native lifecycle hooks or SessionStart integration (deferred)

### 1.3 Intended Audience

Contributors to the SRD plugin. The requirements-analyst agent definition and
codebase-mapping skill are the implementation targets.

### 1.4 Definitions and Acronyms

See [GLOSSARY.md](GLOSSARY.md).

---

## 2. Overall Description

### 2.1 Product Perspective

This feature modifies the requirements-analyst agent's Phase 1 (Orientation) behaviour
and Section 4 (Codebase Context) usage patterns. It changes the codebase mapping from
an opt-in offer ("Want me to map it?") to an automatic background task.

### 2.2 Product Functions (Summary)

| Function | Description |
|----------|-------------|
| F-01 | Auto-trigger codebase mapping at session start |
| F-02 | Staleness check before rescanning |
| F-03 | Greenfield detection and silent skip |
| F-04 | Overlay codebase context at next reflection checkpoint |
| F-05 | Progressive disclosure: broad map then targeted deep dives |

### 2.3 User Classes and Characteristics

| Actor | Description | Frequency of Use | Technical Proficiency |
|-------|-------------|-------------------|----------------------|
| Facilitation User | Person using the requirements-analyst agent | Every session | Varies |

The user does not interact with this feature directly. It operates transparently.

### 2.4 Assumptions and Dependencies

- The requirements-analyst agent reliably follows MUST-level Phase 1 instructions
- The Agent tool's `run_in_background: true` parameter works within agent sessions
- Filesystem modification times are reliable indicators of codebase changes

---

## 3. System Features

### 3.1 Auto-Trigger [F-01]

**Priority:** High

#### 3.1.1 Description

When the requirements-analyst agent begins a session, it checks for a meaningful
codebase in the working directory and triggers the codebase-mapping skill as a
background task without user interaction.

#### 3.1.2 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-01 | The agent MUST check for a meaningful codebase on first turn | H | Mapping triggered before first user-facing question |
| FR-02 | The mapping MUST run as a background task | H | Facilitation conversation is not blocked |
| FR-03 | The agent MUST NOT ask permission before mapping | H | No "Want me to map it?" prompt |
| FR-04 | The agent MUST NOT mention the mapping to the user | H | No "I'm mapping your codebase" message |

---

### 3.2 Staleness Check [F-02]

**Priority:** High

#### 3.2.1 Description

Before performing a full scan, check whether an existing CODEBASE_INDEX.json is still
current by comparing its timestamp against filesystem modification times.

#### 3.2.2 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-05 | If CODEBASE_INDEX.json exists, the mapper MUST read `mapped_at` timestamp | H | Timestamp extracted before any scan |
| FR-06 | The mapper MUST compare `mapped_at` against source file mtimes | H | Comparison uses filesystem modification times, not git history |
| FR-07 | If no source files modified since `mapped_at`, the mapper MUST skip the scan | H | Existing index reused without modification |
| FR-08 | If source files have changed, the mapper MUST perform a full rescan | H | New index overwrites the old one |
| FR-09 | The mtime check MUST exclude ignored directories (node_modules, .git, vendor, etc.) | H | Only source-relevant directories checked |

#### 3.2.3 Business Rules

| ID | Rule | Applies To |
|----|------|------------|
| BR-01 | "Changed" means any source file mtime is newer than `mapped_at` | FR-06 |
| BR-02 | Uncommitted work (new files, WIP changes) MUST be detected | FR-06 |

---

### 3.3 Greenfield Detection [F-03]

**Priority:** High

#### 3.3.1 Description

Detect when no meaningful codebase exists and skip mapping silently.

#### 3.3.2 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-10 | A directory with no package manifests and no source files is greenfield | H | See greenfield criteria in BR-03 |
| FR-11 | Greenfield detection MUST exit immediately with no output | H | No CODEBASE_INDEX.json created |
| FR-12 | The agent MUST NOT mention the absence of a codebase | H | No "I didn't find a codebase" message |

#### 3.3.3 Business Rules

| ID | Rule | Applies To |
|----|------|------------|
| BR-03 | Greenfield = no package manifests (package.json, requirements.txt, go.mod, Cargo.toml, pom.xml, build.gradle, Gemfile, composer.json, *.csproj, *.sln, Package.swift, mix.exs) AND no source files (.ts, .py, .go, .rs, .java, .rb, .php, .cs, .swift, .ex, .exs) | FR-10 |

---

### 3.4 Overlay at Reflection Checkpoint [F-04]

**Priority:** High

#### 3.4.1 Description

When the background mapping completes mid-conversation, the agent weaves codebase
context into the next natural reflection checkpoint rather than interrupting.

#### 3.4.2 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-13 | The agent MUST NOT interrupt the conversation when mapping completes | H | No standalone "mapping complete" message |
| FR-14 | Codebase context MUST be introduced at the next reflection checkpoint | H | Context woven into the 3-4 exchange reflection |
| FR-15 | The overlay MUST reference topics already discussed | H | Connects codebase findings to what the user has said |
| FR-16 | The overlay MUST use domain language, not infrastructure language | H | "A module that handles user registration" not "Express with PostgreSQL" |

---

### 3.5 Progressive Disclosure [F-05]

**Priority:** High

#### 3.5.1 Description

Codebase context operates at two depth levels: a broad initial map and on-demand
deep dives triggered by conversation focus.

#### 3.5.2 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-17 | The initial map (Level 1) captures modules, services, and their apparent responsibilities | H | 50,000ft view from directory structure and patterns |
| FR-18 | When conversation narrows to a specific area, the agent MUST read relevant source files (Level 2) | H | Deep dive happens by reading files, not re-running the mapper |
| FR-19 | Level 2 deep dives MUST inform the agent's questions with actual business logic | H | Questions reference specific validation rules, data relationships, workflows found in code |

---

## 4. Non-Functional Requirements

See [NFR.md](NFR.md).

---

## 5. Diagrams

| Diagram Type | File | Purpose |
|-------------|------|---------|
| Process Flow | [diagrams/process-flows.md](diagrams/process-flows.md) | Auto-trigger decision flow |
| State | [diagrams/state-diagrams.md](diagrams/state-diagrams.md) | Mapping task lifecycle |

---

## 6. Traceability Matrix

| Goal | Features | Requirements | Diagrams |
|------|----------|-------------|----------|
| Map codebase without user action | F-01 | FR-01–FR-04 | process-flows |
| Avoid redundant scans | F-02 | FR-05–FR-09 | process-flows |
| Handle greenfield silently | F-03 | FR-10–FR-12 | process-flows |
| Overlay at natural pause | F-04 | FR-13–FR-16 | state-diagrams |
| Depth matches conversation focus | F-05 | FR-17–FR-19 | — |
