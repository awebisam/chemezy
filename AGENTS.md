# AGENTS.md

## Non-Negotiable Rules

1. Code is the primary source of truth. When sources conflict, trust them in this order:
   - `app/` Python code
   - `app/schemas/`, `app/models/`, `app/api/`, `app/services/`
   - `alembic/` migrations
   - `scripts/` and actual runtime defaults
   - checked-in database shape and current `openapi.json`
   - `README.md`, `.kiro/*`
2. Do not use `CLAUDE.md` as a primary source. It is a compatibility pointer to this file, not an independent spec.
3. If you change any code, schema, model, route, enum, effect, environment value, command, dependency, migration, operational workflow, or caveat described here, you MUST update this file in the same patch.
4. The previous rule is recursive and mandatory. If you edit the codebase and this file becomes even slightly inaccurate, stale, incomplete, or misleading, update this file before you finish.
5. Do not defer `AGENTS.md` updates to "later". Keep it synchronized in the same change.
6. `AGENTS.md` is the canonical agent-instructions file for this repo. `CLAUDE.md` exists only as a compatibility shim for tools that auto-discover that filename. Do not maintain two divergent instruction documents.

## What This Repo Is

Chemezy is a FastAPI backend for a chemistry game/simulation. It combines:

- JWT-based user auth
- a chemical database backed by SQLModel
- DSPy-driven chemical creation and reaction prediction
- PubChem retrieval for chemistry grounding
- deterministic reaction caching
- world-first effect discovery tracking
- a multi-service award / leaderboard / notification / admin system
- admin monitoring and feature/config management

The FastAPI app lives in `app/main.py`. API routes are mounted under `/api/v1`. The root `/` serves `index.html`, and `/static/*` serves the no-build frontend assets. `/health` returns HTTP 200.

## Runtime Defaults

- Python web framework: FastAPI
- ORM / models: SQLModel on top of SQLAlchemy
- default database: `sqlite:///./chemezy.db`
- auth: JWT using `SECRET_KEY` and `HS256`
- app entrypoint: `app.main:app`
- dev server: `uvicorn app.main:app --reload`
- docs: `/docs` and `/redoc`
- test-mode rate limit bypass: `settings.testing` overrides the limiter dependency

Important environment/config facts from code:

- `SECRET_KEY` is required. There is no safe default in code.
- `database_url` defaults to SQLite, not PostgreSQL.
- `dspy_enabled` defaults to `True`.
- Azure OpenAI settings are optional. If missing, DSPy may remain unconfigured.
- `allowed_origins` exists in settings, but `app.main` currently hardcodes `["*"]` in CORS middleware instead of reading the setting.
- frontend assets are served directly by FastAPI from the checked-in `static/` directory; there is no Node/Vite build step in code
- the authenticated frontend is modal-first: the page shows a launcher/summary panel, while the full chemistry playground opens in an overlay with a scrollable compound deck above the beaker

## Safe Local Commands

Use these as the current canonical local commands:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Useful URLs once running:

- `http://localhost:8000/`
- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Repo Map

- `app/main.py`: FastAPI app, CORS, static asset mount, startup DSPy setup, root, health, global exception handler
- `app/api/v1/api.py`: router aggregation
- `app/api/v1/endpoints/`: all HTTP endpoints
- `app/core/config.py`: environment settings
- `app/core/security.py`: password hashing, JWT create/verify
- `app/core/dspy_manager.py`: global DSPy LM setup
- `app/models/`: SQLModel tables and related model schemas
- `app/schemas/`: Pydantic request/response schemas and enums
- `app/services/`: business logic
- `app/db/session.py`: SQLModel engine and session dependency
- `alembic/`: migrations
- `index.html`: frontend HTML shell mounted at `/`, including the authenticated launcher panel and the modal chemistry playground
- `static/css/app.css`: shared frontend theme and animation CSS
- `static/js/`: no-build Alpine ES modules for app store, panels, beaker renderer, and helpers
- `static/js/components/lab-svg/`: swappable SVG builder modules for structural lab art such as the beaker shell, compound deck, and test tubes
- `static/svg/effect-sprites.svg`: reusable SVG sprite sheet for beaker effect layers
- `scripts/seed_awards.py`: award template seed script
- `scripts/run_tests.sh`: shell-test runner that resets the database
- `scripts/optimize_database.py`: SQLite optimization / index / view script
- `tests/`: shell-based API and integration tests

## Current HTTP Surface

These are the actual route groups mounted by code.

### Root-Level Routes

- `GET /`
- `GET /health`
- `GET /static/{path:path}`

### Auth and Users: `/api/v1/auth`

- `POST /register`
- `POST /token`
- `GET /me`
- `GET /users/{user_id}`

### Reactions: `/api/v1/reactions`

- `POST /react`
- `GET /cache`
- `GET /stats`

### Chemicals: `/api/v1/chemicals`

- `POST /`
- `GET /`
- `GET /{chemical_id}`
- `DELETE /{chemical_id}`

### Debug: `/api/v1/debug`

- `DELETE /reactions/clear`
- `DELETE /reactions/{reaction_id}`
- `DELETE /chemicals/clear`
- `DELETE /chemicals/{chemical_id}`

### Awards: `/api/v1/awards`

- `GET /me`
- `GET /available`
- `GET /leaderboard/{category}`
- `GET /user/{user_id}`
- `GET /leaderboard/overall`
- `GET /leaderboard/my-rank`
- `GET /community/recent-achievements`
- `GET /community/statistics`
- `GET /dashboard/stats`
- `GET /dashboard/recent`
- `GET /dashboard/progress`
- `GET /notifications`
- `POST /notifications/read`

### Admin Awards: `/api/v1/admin/awards`

- `POST /templates`
- `GET /templates`
- `GET /templates/{template_id}`
- `PUT /templates/{template_id}`
- `POST /templates/{template_id}/activate`
- `POST /templates/{template_id}/deactivate`
- `POST /awards/grant`
- `POST /awards/revoke`

### Admin Monitoring: `/api/v1/admin/monitoring`

- `GET /audit-logs`
- `GET /system-health`
- `GET /user-activity/{user_id}`
- `GET /alerts`
- `POST /cleanup-logs`
- `GET /dashboard`

### Admin Config: `/api/v1/admin/config`

- `GET /info`
- `GET /feature-flags`
- `GET /feature-flags/{feature_name}`
- `POST /feature-flags/{feature_name}/toggle`
- `POST /reload`
- `GET /user-features`
- `GET /system-status`

## Auth and Access Rules

- OAuth2 bearer token dependency is defined in `app/api/v1/endpoints/users.py`.
- `POST /api/v1/auth/register` is rate-limited to `5/minute`.
- `POST /api/v1/auth/token` is rate-limited to `10/minute`.
- `get_current_admin_user` checks `User.is_admin`.
- `GET /api/v1/chemicals/` and `GET /api/v1/chemicals/{chemical_id}` are public.
- `POST /api/v1/chemicals/` and `DELETE /api/v1/chemicals/{chemical_id}` require authentication, not admin.
- reaction endpoints require authentication.
- debug clear endpoints require admin.
- debug deletion-request endpoints require authentication.
- awards endpoints require authentication.
- all `/api/v1/admin/*` endpoints require admin.

## Canonical Request and Response Shapes

These are the current schema truths from code. Do not replace them with README examples if they disagree.

### Reaction Request

`ReactionRequest` is:

```json
{
  "reactants": [
    {
      "chemical_id": 1,
      "quantity": 1.0
    }
  ],
  "environment": "Earth (Normal)",
  "catalyst_id": null
}
```

Important:

- `reactants` is a list of objects, not a list of formula strings.
- `environment` must be one of the enum values listed below.
- `catalyst_id` is optional.

### Reaction Response

`ReactionPrediction` currently contains:

```json
{
  "products": [
    {
      "chemical_id": 4,
      "molecular_formula": "H2O",
      "common_name": "Water",
      "quantity": 1.0,
      "is_soluble": true
    }
  ],
  "effects": [],
  "explanation": "Fallback prediction.",
  "is_world_first": false,
  "state_of_product": null
}
```

Important:

- `state_of_product` is deprecated but still present as an optional field in the schema.
- cached reactions are converted back into `ProductOutput` items.
- fallback prediction returns the input chemicals as products, no effects, and `"Fallback prediction."`.

### Chemical Creation Request

`ChemicalCreate` is:

```json
{
  "molecular_formula": "NaCl",
  "context": "table salt"
}
```

`context` is optional and used to disambiguate compounds during DSPy generation.

### Notification Mark-Read Request

`POST /api/v1/awards/notifications/read` expects:

```json
{
  "notification_ids": ["award_1", "award_2"]
}
```

It does not accept a bare JSON array.

## Enums and Canonical Value Sets

### Environment Enum

These are the only valid `ReactionRequest.environment` values:

- `Earth (Normal)`
- `Vacuum`
- `Pure Oxygen`
- `Inert Gas`
- `Acidic Environment`
- `Basic Environment`

### State of Matter Enum

Current `StateOfMatter` values:

- `solid`
- `liquid`
- `gas`
- `plasma`
- `aqueous`

### AwardCategory Enum

Current API/category values:

- `discovery`
- `database_contribution`
- `community`
- `special`
- `achievement`

## Complete Effect Catalog

All supported effect types live in `app/schemas/effects.py`. If an effect is added, removed, renamed, or reshaped, update this section immediately.

### `gas_production`

Fields:

- `effect_type`: `"gas_production"`
- `gas_type`: string
- `color`: string
- `intensity`: float in `[0.0, 1.0]`
- `duration`: float `> 0`

### `light_emission`

Fields:

- `effect_type`: `"light_emission"`
- `color`: string
- `intensity`: float in `[0.0, 1.0]`
- `radius`: float `> 0`
- `duration`: float `> 0`

### `volume_change`

Fields:

- `effect_type`: `"volume_change"`
- `factor`: float `> 0`

### `spill`

Fields:

- `effect_type`: `"spill"`
- `amount_percentage`: float in `[0.0, 1.0]`
- `spread_radius`: float `> 0`

### `state_change`

Fields:

- `effect_type`: `"state_change"`
- `product_chemical_id`: integer
- `final_state`: string

### `temperature_change`

Fields:

- `effect_type`: `"temperature_change"`
- `delta_celsius`: float

### `texture_change`

Fields:

- `effect_type`: `"texture_change"`
- `product_chemical_id`: integer
- `texture_type`: string
- `color`: string
- `viscosity`: float in `[0.0, 1.0]`

### `foam_production`

Fields:

- `effect_type`: `"foam_production"`
- `color`: string
- `density`: float `> 0`
- `bubble_size`: one of `small`, `medium`, `large`
- `stability`: float `> 0`

## Core Service Behavior

### Chemical Creation

`ChemicalService`:

- uses `PubChemService` first
- feeds PubChem data plus optional `context` into DSPy
- normalizes returned data into `ChemicalGenerated`
- deduplicates by `(molecular_formula, common_name)`
- creates DB rows only if the exact formula/name pair does not already exist

### Reaction Prediction

`ReactionService`:

- loads reactants by `chemical_id`
- serializes reactants into JSON for DSPy
- includes optional catalyst data
- builds a deterministic SHA-256 cache key from sorted reactant JSON + environment + catalyst
- checks `reaction_cache` first
- if no cache hit and DSPy is configured, predicts via `ChemistryReasoningModule(PredictReactionProductsAndEffects)`
- creates missing product chemicals via `ChemicalService.get_or_create_chemical`
- stores reaction results in `reaction_cache`
- checks effects for world-first discovery via `discovery`
- evaluates discovery awards after a new discovery

### Awards

Award functionality is split across:

- `AwardTemplateService`: CRUD + validation
- `AwardEvaluator`: criteria checks, progress, tiering
- `AwardService`: grant / revoke / retrieval orchestration
- `LeaderboardService`: category and overall leaderboards + community feed
- `NotificationService`: dashboard stats, recent awards, pseudo-notifications
- `AuditService`: audit retrieval and system/activity summaries
- `ConfigurationService`: feature flags and award-system runtime config

## Current Database Model Set

Current SQLModel definitions include:

- `User`
- `Chemical`
- `ReactionCache`
- `Discovery`
- `DeletionRequest`
- `AwardTemplate`
- `UserAward`
- `AuditLog`

Current checked-in SQLite database at Alembic head contains these tables:

- `alembic_version`
- `chemicals`
- `award_templates`
- `deletionrequest`
- `discovery`
- `reaction_cache`
- `user`
- `user_awards`

Important mismatch:

- `AuditLog` exists in code, but the current migration head and checked-in SQLite DB do not contain the current audit-log table shape.

## Supported Award Criteria Types

`AwardTemplateService` currently validates only these criteria types:

- `discovery_count`
- `unique_effects`
- `reaction_complexity`
- `debug_submissions`
- `correction_accuracy`
- `data_quality_impact`
- `profile_completeness`
- `consecutive_days`
- `help_others`

If you add or remove a criteria type anywhere, update this section and the caveats below.

## Testing Reality

Testing in this repo is not pytest-driven right now.

- `pytest --collect-only -q` currently collects no tests.
- the real tests are shell scripts in `tests/api/` and `tests/integration/`
- `scripts/run_tests.sh`:
  - kills running `uvicorn app.main:app`
  - deletes `chemezy.db`
  - runs `alembic upgrade head`
  - starts a server with `TESTING=true`
  - references a `tests/services` suite that does not currently exist
- frontend verification is currently manual/browser-based; there is no checked-in JS test runner or frontend build pipeline

Treat `scripts/run_tests.sh` as destructive. Do not run it casually against the checked-in DB if you care about preserving local state.

## Known Mismatches, Stale Docs, and Traps

These are current repo truths that agents must account for.

1. `README.md`, `.kiro/*`, and parts of `openapi.json` are helpful but not fully reliable.
2. `CLAUDE.md` should remain a thin compatibility shim that points back to this file. Do not reintroduce duplicated guidance there.
3. `.env.example` still advertises PostgreSQL, but code defaults to SQLite and `docker-compose.yml` also points at SQLite.
4. `README.md` examples for reactions are stale. Current reaction requests use `chemical_id` objects, not formula strings.
5. Several shell tests are stale. Examples:
   - `tests/integration/test_reaction_flow.sh` sends invalid reaction payloads
   - `tests/api/test_notifications.sh` sends a bare JSON array to `notifications/read`, but code expects `{"notification_ids": [...]}`.
   - `tests/api/test_error_handling.sh` expects rich `error_id` middleware responses, but the app currently relies on the simpler global exception handler in `app.main`.
6. `ErrorHandlingMiddleware` exists in `app/middleware/error_middleware.py` but is not mounted in `app.main`.
7. `app/main.py` has a global `Exception` handler that returns:
   - `{"detail": "Internal server error", "error": str(exc)}`
8. `Dockerfile` uses `python:3.12.7-alpine` but runs `apt-get` and `useradd`. That Dockerfile is not trustworthy without fixing the base-image/package-manager mismatch.
9. GitHub Actions currently install dependencies and deploy, but do not run tests.
10. `scripts/seed_awards.py` contains template definitions with unsupported criteria types such as:
   - `special_event`
   - `special_recognition`
   - `unique_elements`
   - `safety_score`
   The validator does not support those values.
11. The checked-in database currently contains seeded chemicals, users, reactions, discoveries, templates, and awards. Do not assume an empty DB.
12. `admin_config` and several admin/community responses use hardcoded timestamp strings like `2025-01-15T00:00:00Z`.
13. `Config.allowed_origins` exists, but `app.main` does not use it.
14. `ReactionCache.effects` is typed as `list[str]` in the model, but code actually stores effect dictionaries via `effect.model_dump()`.
15. The frontend is now split across `index.html` plus `static/` assets. If the UI breaks before hitting the API, check the `app.main` static mount and the Alpine ES-module boot path before assuming backend regressions.

## What To Update In This File When The Code Changes

If you touch any of the following, update this file in the same patch:

- route inventory
- auth/access rules
- request/response shapes
- enums
- supported effect types or effect fields
- award criteria types
- service responsibilities
- runtime commands
- environment variables or defaults
- frontend asset structure or static-serving workflow
- database model inventory or migration caveats
- testing workflow
- known mismatches and traps

If you are unsure whether a change requires an `AGENTS.md` update, assume that it does.

## Editing Guidance For Future Agents

- Keep business logic in services, not endpoint functions.
- Keep schema changes synchronized across:
  - SQLModel models
  - Pydantic schemas
  - services
  - routes
  - Alembic migrations
  - this file
- Route new AI behavior through DSPy signatures/modules, not ad hoc prompts.
- Prefer documenting observed code behavior over intended behavior.
- When code and docs disagree, fix docs or explicitly record the mismatch here.
