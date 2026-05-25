# Glossary: Auto Codebase Mapping

| Term | Definition | Context |
|------|-----------|---------|
| Codebase mapping | The process of scanning a project directory to produce a structured index of its technology stack, services, data models, and integrations | Background task run by the codebase-mapping skill |
| CODEBASE_INDEX.json | JSON file containing the structured output of a codebase mapping scan | Stored in the specification folder |
| Greenfield | A project directory with no meaningful source code or package manifests | Detected to skip mapping silently |
| Staleness check | Comparison of an existing index's timestamp against source file modification times to determine if a rescan is needed | Runs before every mapping attempt |
| Reflection checkpoint | A facilitation pause every 3-4 exchanges where the agent mirrors back understanding | The point where codebase context is overlaid |
| Domain map (Level 1) | Broad, shallow view of the codebase — modules, services, and their apparent responsibilities | Produced by the initial background scan |
| Deep dive (Level 2) | Targeted reading of specific source files to understand actual business logic in an area the conversation has focused on | Triggered on-demand by conversation focus |
| Domain language | Language that describes what a system does (capabilities, responsibilities) rather than how it is built (frameworks, databases) | Required for overlay during facilitation |
| Infrastructure language | Language that describes technology choices (Express, PostgreSQL, Redis) rather than domain capabilities | Belongs in the index, not in facilitation conversation |
| mtime | Filesystem modification timestamp of a file | Used for staleness comparison |

## Synonyms and Disambiguation

| Preferred Term | Also Known As | NOT the Same As |
|---------------|---------------|--------------------|
| Codebase mapping | Codebase scan, code indexing | Static analysis, linting |
| Greenfield | New project, empty project | Brownfield (existing codebase) |
| Overlay | Context introduction, weaving in | Interruption, announcement |
| Deep dive | Zoom in, drill down | Full rescan |
