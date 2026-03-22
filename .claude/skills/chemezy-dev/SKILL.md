---
name: chemezy-dev
description: >
  Use when working on the Chemezy FastAPI backend: adding or modifying API endpoints, creating or
  updating SQLModel database models, writing Pydantic schemas, building services, creating Alembic
  migrations, configuring DSPy signatures, or touching any Python code. Also use when the user
  mentions reactions, chemicals, awards, leaderboards, authentication, admin endpoints, caching,
  PubChem, or any backend feature. Trigger even for seemingly simple backend changes — the
  multi-layer synchronization requirements (models, schemas, services, routes, migrations, AGENTS.md)
  make every change non-trivial.
---

# Chemezy Backend Development

You are working on the **Chemezy** backend — a FastAPI application that powers a 2D sandbox chemistry simulation game for education. The backend is the source of truth for all chemistry logic. The frontend is a thin client that sends requests and renders responses.

## The Golden Rule: AGENTS.md Sync

**Every code change requires an AGENTS.md update in the same patch.** This is non-negotiable and recursive — if your change makes any part of AGENTS.md inaccurate, stale, incomplete, or misleading, you must fix it before finishing.

Read `AGENTS.md` before starting any work. It contains the current truth about routes, schemas, enums, effects, services, models, known mismatches, and traps.

## Architecture Overview

```
app/
├── main.py              # FastAPI app, CORS, static mount, startup, health, global exception handler
├── core/
│   ├── config.py        # Settings from env vars (pydantic-settings)
│   ├── security.py      # Password hashing (passlib) + JWT (python-jose)
│   └── dspy_manager.py  # Global DSPy LM setup
├── models/              # SQLModel tables
├── schemas/             # Pydantic request/response schemas + enums
│   └── effects.py       # The 8 Effect types as discriminated union
├── services/            # All business logic lives here, NOT in endpoints
├── api/v1/
│   ├── api.py           # Router aggregation
│   └── endpoints/       # Thin HTTP handlers that call services
├── db/
│   └── session.py       # SQLModel engine + session dependency
└── middleware/
    └── error_middleware.py  # EXISTS but NOT mounted
```

## Synchronization Checklist (Every Feature)

When adding anything — a field, endpoint, enum value, effect type — touch all layers:

1. **Model** (`app/models/`): Add/modify SQLModel table
2. **Migration** (`alembic/`): `alembic revision --autogenerate -m "description"`, then review
3. **Schema** (`app/schemas/`): Add/modify Pydantic request/response schemas
4. **Service** (`app/services/`): Implement business logic — keep endpoints thin
5. **Endpoint** (`app/api/v1/endpoints/`): Wire up HTTP route, calling the service
6. **Router** (`app/api/v1/api.py`): Register new routers if needed
7. **AGENTS.md**: Update relevant sections

## Key Patterns

### Service Pattern
All business logic goes in services, not endpoints. Endpoints are thin wrappers:

```python
@router.post("/react")
async def react(request: ReactionRequest, db: Session = Depends(get_session),
                current_user: User = Depends(get_current_user)):
    service = ReactionService(db)
    return await service.predict_reaction(request, current_user.id)
```

### DSPy Pattern
Chemistry AI is routed through DSPy Signatures + ChemistryReasoningModule (COT + reflection). Don't use ad-hoc prompts.

### Reaction Cache Pattern
Deterministic: same inputs always produce same outputs via SHA-256 cache key from `sorted_reactants_json + environment + catalyst_data`. Cache hit returns cached result. Cache miss triggers DSPy prediction, stores in cache, checks discoveries.

### Chemical Creation Pipeline
`ChemicalService.get_or_create_chemical`: PubChem lookup -> DSPy generation -> normalize to `ChemicalGenerated` -> deduplicate by `(molecular_formula, common_name)` -> create DB row if new.

## Quick Reference: Valid Enum Values

| Category | Values |
|----------|--------|
| Environments | `Earth (Normal)`, `Vacuum`, `Pure Oxygen`, `Inert Gas`, `Acidic Environment`, `Basic Environment` |
| States of Matter | `solid`, `liquid`, `gas`, `plasma`, `aqueous` |
| Award Categories | `discovery`, `database_contribution`, `community`, `special`, `achievement` |
| Effect Types | `gas_production`, `light_emission`, `volume_change`, `spill`, `state_change`, `temperature_change`, `texture_change`, `foam_production` |

## Environment & Auth

- **Database**: SQLite by default (`sqlite:///./chemezy.db`), not PostgreSQL despite `.env.example`
- **Auth**: JWT with `HS256`, tokens from `POST /api/v1/auth/token` (form-urlencoded)
- **Rate limiting**: `5/min` register, `10/min` token, bypassed when `settings.testing = True`
- **CORS**: Hardcoded `["*"]` in `app.main` (settings.allowed_origins exists but isn't used)
- **DSPy**: Azure OpenAI by default, configurable via env vars

## Dev Commands

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Known Traps

1. `ReactionCache.effects` typed `list[str]` but stores dicts via `effect.model_dump()`
2. `ErrorHandlingMiddleware` exists but is NOT mounted
3. `scripts/seed_awards.py` references unsupported criteria types
4. Dockerfile uses alpine but runs `apt-get` — broken
5. Frontend served from `static/` — no Node/Vite build step
6. `AuditLog` model exists in code but migration head doesn't match it
7. Several shell tests in `tests/` are stale — check AGENTS.md for specifics
8. `scripts/run_tests.sh` is destructive (drops DB)
