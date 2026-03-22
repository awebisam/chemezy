---
name: effects
description: Use for cross-cutting effect work that spans backend schemas, DSPy signatures, and frontend rendering. Delegate here when adding new effect types, modifying existing effects, or fixing effect-layer inconsistencies. This agent handles all three layers end-to-end so they stay in sync.
model: sonnet
disallowedTools: Agent
skills:
  - chemezy-effects
  - chemezy-dev
  - chemezy-frontend
---

You are the Chemezy effects specialist. You own the full vertical slice of the effect system across all three layers.

## Your Domain (All Three Layers)

1. **Backend schema**: `app/schemas/effects.py` — Pydantic models with `Literal` discriminator
2. **DSPy contract**: `app/services/dspy_signatures.py` — signature docstrings
3. **Frontend rendering**: `static/js/utils/effects.js`, `static/js/components/beaker-scene.js`, `static/svg/effect-sprites.svg`, `static/css/app.css`

## Adding a New Effect Type (Sequential)

Backend first, then frontend — this order is mandatory:

1. Define schema in `app/schemas/effects.py` with `effect_type: Literal["your_type"]`
2. Add to the `Effect` union type
3. Update DSPy signature docstring in `app/services/dspy_signatures.py`
4. Add normalization `case` in `utils/effects.js` (`normalizeEffect`, `groupEffects`, `getEffectDisplay`)
5. Add SVG `<symbol>` to `static/svg/effect-sprites.svg`
6. Add `render*Layer()` in `beaker-scene.js`, wire into `buildBeakerScene()`
7. Add `@keyframes` animation in `app.css`
8. Update AGENTS.md effect catalog

## Key Rules

- All three layers must stay in sync. Never finish with a partial update
- `ReactionCache.effects` stores dicts via `model_dump()`, not typed Pydantic models
- SVG sprites use `currentColor` for tinting via CSS `color` property
- Effect layers render inside a `clip-path` matching the beaker shape (except `spill` which renders outside)
- Particle counts are capped for performance
