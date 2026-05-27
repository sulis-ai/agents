---
name: codebase-mapping
description: "Maps an existing codebase so requirements work can build on what's there."
---

# Codebase Mapping

When invoked, map the current codebase to build a context index for requirements facilitation.
Run this as a background task — it should not block the facilitation conversation.

If arguments are provided, treat them as the path to map (default: current working directory).

After mapping, report a brief summary and note how the codebase context will inform the
requirements conversation.

---

## Execution Model

The codebase mapper runs synchronously at the start of the facilitation session.

- Triggered by the requirements-analyst agent at session start (brownfield projects
  only), or manually via `/sulis:codebase-mapping`
- The agent waits for mapping to complete before asking its first facilitation question,
  because the index informs question selection and grounding
- After mapping, the agent briefly acknowledges what it found before proceeding
- If no meaningful codebase exists (greenfield project, docs-only repo, empty directory
  with just a README), the mapper exits immediately and silently. The agent proceeds
  without a codebase index and does not mention the absence.

### Staleness Check

Before performing a full scan, check whether a CODEBASE_INDEX.json already exists in
the specification folder. If it does:

1. Read the `mapped_at` timestamp from the existing index
2. Compare against filesystem modification times of source files in the project
   (not node_modules, .git, or other excluded directories)
3. If no source files have been modified since `mapped_at`, skip the scan and reuse
   the existing index
4. If source files have changed, perform a full rescan and overwrite the index

This avoids redundant scans across sessions when the codebase has not changed.

### Greenfield Detection

A directory is considered "greenfield" (no meaningful codebase) when:
- No package manifests exist (package.json, requirements.txt, go.mod, etc.)
- No source files exist (.ts, .py, .go, .rs, .java, .rb, .php, .cs, etc.)
- Only configuration files, documentation, or empty directories are present

When greenfield is detected, exit immediately with no output and no notification.

---

## Mapping Process

### Step 1: Walk Project Structure

Traverse the project directory tree to understand the layout.

**Skip directories:**
- `node_modules`
- `.git`
- `vendor`
- `dist`
- `build`
- `__pycache__`
- `.venv`
- `venv`
- `target`
- `.next`
- `.nuxt`
- `coverage`
- `.tox`
- `egg-info`

**Record:**
- Top-level directory names and their apparent purpose
- Monorepo structure (apps/, packages/, services/, libs/)
- Configuration files at the root level

### Step 2: Read Package Manifests

Identify the technology stack by reading package manifests. Check for:

| Manifest | Ecosystem |
|----------|-----------|
| `package.json` | Node.js / JavaScript / TypeScript |
| `requirements.txt` | Python (pip) |
| `pyproject.toml` | Python (modern) |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `pom.xml` | Java (Maven) |
| `build.gradle` / `build.gradle.kts` | Java / Kotlin (Gradle) |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `*.csproj` / `*.sln` | .NET / C# |
| `Package.swift` | Swift |
| `mix.exs` | Elixir |

**Extract from manifests:**
- Language and version
- Framework (from dependencies)
- Database drivers (to infer database technology)
- Testing frameworks
- Build tools
- Notable libraries that indicate patterns (e.g., `@nestjs/core` indicates NestJS architecture)

### Step 3: Identify Technology Stack

Combine manifest analysis with file extension survey:

- `.ts` / `.tsx` — TypeScript
- `.py` — Python
- `.go` — Go
- `.rs` — Rust
- `.java` — Java
- `.rb` — Ruby
- `.php` — PHP
- `.cs` — C#
- `.swift` — Swift
- `.ex` / `.exs` — Elixir

Identify frameworks from dependency names and import patterns.

### Step 4: Search for Architectural Patterns

Search the codebase for common patterns using grep-style analysis.

**Routes:**
- `@app.route`, `@router.` (Python/Flask/FastAPI)
- `router.get`, `router.post`, `app.get`, `app.post` (Express/Node)
- `@Controller`, `@GetMapping`, `@PostMapping` (Spring/Java)
- `@Get()`, `@Post()`, `@Controller()` (NestJS)
- `resources :`, `get '/'`, `post '/'` (Rails)
- `Route::get`, `Route::post` (Laravel)

**Models / Entities:**
- `@Entity`, `@Table` (JPA/Hibernate)
- `class.*Model`, `db.Model` (Django/SQLAlchemy)
- `schema.*Schema`, `mongoose.Schema` (Mongoose)
- `@model`, `@column` (TypeORM/Sequelize)
- `create_table`, `add_column` (migrations)
- `prisma.schema` definitions

**Services:**
- `@Service`, `@Injectable` (Spring/NestJS)
- `class.*Service` (general pattern)
- Files in `services/` or `service/` directories

**API Endpoints:**
- HTTP method decorators and handlers
- OpenAPI/Swagger definitions (`openapi.yaml`, `swagger.json`)
- GraphQL schema definitions (`.graphql` files, `type Query`, `type Mutation`)

**Database:**
- Migration files (directories named `migrations/`, `db/migrate/`)
- ORM configuration files
- Connection strings in configuration (redact credentials)
- Schema definition files

**External Integrations:**
- HTTP client imports (`axios`, `fetch`, `requests`, `http.Client`)
- SDK imports (`@stripe/stripe-node`, `aws-sdk`, `@sendgrid/mail`)
- Webhook handler patterns
- Message queue connections (`amqplib`, `kafka`, `redis` pub/sub)

### Step 5: Map Data Models

From schema files, ORM definitions, and migration files:

- List each entity/model with its key fields
- Identify relationships (one-to-many, many-to-many, belongs-to)
- Note which fields are required vs. optional
- Flag fields that appear to be sensitive (email, password, SSN, credit card)

### Step 6: Identify Service Boundaries

From directory structure and import analysis:

- Which directories represent distinct services or modules?
- What are the internal dependencies between modules?
- Are there shared libraries or packages?
- What is the deployment topology implied by the structure?

---

## Output Format

The mapper produces `CODEBASE_INDEX.json` in the specification folder.

```json
{
  "mapped_at": "ISO-8601 timestamp",
  "project_root": "path",
  "technology_stack": {
    "languages": ["TypeScript", "Python"],
    "frameworks": ["Next.js", "FastAPI"],
    "databases": ["PostgreSQL"],
    "build_tools": ["npm", "poetry"],
    "testing": ["jest", "pytest"]
  },
  "applications": [
    {
      "name": "web-app",
      "path": "apps/web",
      "type": "frontend",
      "framework": "Next.js"
    }
  ],
  "services": [
    {
      "name": "auth-service",
      "path": "src/services/auth",
      "responsibilities": ["authentication", "authorization"]
    }
  ],
  "shared_modules": [
    {
      "name": "utils",
      "path": "packages/utils",
      "purpose": "shared utilities"
    }
  ],
  "integrations": {
    "internal": [
      {
        "from": "web-app",
        "to": "api",
        "protocol": "REST",
        "pattern": "request-response"
      }
    ],
    "external": [
      {
        "system": "Stripe",
        "purpose": "payments",
        "sdk": "@stripe/stripe-node"
      }
    ]
  },
  "data_models": [
    {
      "name": "User",
      "location": "src/models/user.ts",
      "key_fields": ["id", "email", "role"]
    }
  ],
  "routes": [
    {
      "path": "/api/users",
      "method": "GET",
      "handler": "UserController.list"
    }
  ],
  "patterns": ["monorepo", "REST API", "server-side rendering"]
}
```

---

## Usage by the Requirements Analyst

Once CODEBASE_INDEX.json is available, the requirements facilitation agent uses it to:

### Ground Questions in Existing Code
Instead of asking "Do you have user authentication?", the agent can ask "I see there's
an auth-service handling login and authorisation. Will the new feature use the same
authentication flow, or does it need something different?"

### Form Hypotheses About Where New Functionality Fits
"Based on the project structure, it looks like new API endpoints go in `apps/api/routes/`.
Would this new feature follow that same pattern?"

### Identify Existing Patterns to Follow or Diverge From
"The current services all use REST with JSON. Does this new integration also use REST,
or is there a reason to use something different like webhooks or message queues?"

### Spot Integration Points and Potential Conflicts
"The User model currently has fields for id, email, and role. The feature you're describing
would need to add profile information. Would that extend the User model or become a
separate Profile entity?"

### Inform NFR Discussions
"The current stack uses PostgreSQL with no caching layer. If the new feature needs
sub-100ms responses, we might need to specify caching requirements. What kind of
response times are you expecting?"

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2026-03-13 | Initial version | Standards team |
| 2026-03-13 | Renamed from codebase-mapper. Merged map-codebase command. | Standards team |
| 2026-03-13 | Auto-trigger at session start, staleness check, greenfield detection, domain-focused overlay | Standards team |
| 2026-03-17 | Changed execution model from background to synchronous. Agent now waits for mapping to complete before starting facilitation. Experimental async hook scripts added as optional alternative. | Standards team |
