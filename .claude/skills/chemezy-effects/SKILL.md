---
name: chemezy-effects
description: >
  Use when adding new effect types, modifying existing effects, designing visual representations for
  chemical phenomena, updating the SVG sprite sheet, writing effect-related DSPy signature changes,
  or connecting backend effect schemas to frontend rendering. Trigger when the user mentions effects,
  animations, visual feedback, gas production, light emission, foam, spills, temperature changes,
  texture, state changes, volume changes, bubbles, sparks, vapor, or anything about how reactions
  look in the beaker.
---

# Chemezy Effects System

The effect system spans three synchronized layers. All three must stay in sync when you make changes.

## The Three Layers

### Layer 1: Backend Schema (`app/schemas/effects.py`)
Pydantic models with `Literal` discriminator. The `Effect` type is a `Union` of all effect models. This is what DSPy outputs and what gets cached in `ReactionCache.effects`.

### Layer 2: DSPy Contract (`app/services/dspy_signatures.py`)
`PredictReactionProductsAndEffects` signature tells the LLM to produce effects. When adding a new effect type, ensure the signature's docstring covers it.

### Layer 3: Frontend Rendering
Three files work together:
- **`static/js/utils/effects.js`** — Normalization, grouping, display metadata
- **`static/js/components/beaker-scene.js`** — SVG render functions per effect type
- **`static/svg/effect-sprites.svg`** — Reusable SVG `<symbol>` elements
- **`static/css/app.css`** — CSS keyframe animations

## Current Effect Catalog

### `gas_production`
Gas bubbles, vapor, or smoke rising from liquid surface.

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `gas_type` | string | any | Preset: "bubbles"->`bubble-cluster`, "vapor"->`vapor-plume`, "smoke"->`smoke-plume` |
| `color` | string | CSS color | Tints gas sprites |
| `intensity` | float | 0.0-1.0 | Particle count (2-8) and opacity |
| `duration` | float | >0 (0.8-18) | Animation cycle length |

### `light_emission`
Glow and ray-burst centered in beaker.

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `color` | string | CSS color | Glow and ray color |
| `intensity` | float | 0.0-1.0 | Glow radius opacity |
| `radius` | float | >0 (0.3-6) | Base glow circle radius |
| `duration` | float | >0 (0.8-18) | Pulse animation duration |

### `volume_change`
Liquid level expansion or contraction.

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `factor` | float | >0 (0.25-2.5) | Multiplier on volume. >1 = expansion, <1 = contraction |

CSS classes: `beaker--swelling` (>1.08), `beaker--shrinking` (<0.94).

### `spill`
Material overflowing beaker rim. Rendered OUTSIDE the clip-path.

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `amount_percentage` | float | 0.0-1.0 | Volume fraction that spills |
| `spread_radius` | float | >0 (0.15-6) | Puddle spread distance |

### `state_change`
Product transitions to different state of matter.

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `product_chemical_id` | int | - | Which product changes state |
| `final_state` | string | solid/liquid/gas/plasma/aqueous | Target state |

Dispatches to: `renderSolidState` (crystals), `renderGasState` (vapor), `renderPlasmaState` (sparks+glow), `renderAqueousState` (shimmer), `renderLiquidState` (wave).

### `temperature_change`
Exothermic or endothermic reaction.

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `delta_celsius` | float | clamped +/-250 | Positive=heating, negative=cooling |

Positive: warm wave + sparks (orange/gold). Negative: cool specks (pale blue). Shifts liquid colors when |delta| > 20C.

### `texture_change`
Surface texture modification.

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `product_chemical_id` | int | - | Which product affected |
| `texture_type` | string | any | Preset: gooey/slimy->gooey, viscous/sticky->thick, silky->smooth, chalky/crystalline->grainy |
| `color` | string | CSS color | Texture overlay color |
| `viscosity` | float | 0.0-1.0 | Animation speed and opacity |

### `foam_production`
Bubbly cap on liquid surface.

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `color` | string | CSS color | Foam color |
| `density` | float | >0 (0.2-5) | Foam cap width |
| `bubble_size` | enum | small/medium/large | Scale factor (0.75/1.0/1.35) |
| `stability` | float | >0 (0.8-20) | Animation duration |

## Adding a New Effect Type

### Backend
1. Define schema in `app/schemas/effects.py` with `effect_type: Literal["your_type"]` + field validations
2. Add to the `Effect` union type
3. Update DSPy signature docstring in `app/services/dspy_signatures.py`
4. Update AGENTS.md "Complete Effect Catalog" section

### Frontend
5. Add normalization `case` in `utils/effects.js` (`normalizeEffect`, `groupEffects`, `getEffectDisplay`)
6. Add SVG `<symbol>` elements to `static/svg/effect-sprites.svg`
7. Add `render*Layer()` function in `beaker-scene.js`, call from `buildBeakerScene()`
8. Add `@keyframes` animation in `app.css`

## Design Principles

- **Scientifically grounded**: Effects correspond to real observable phenomena
- **Educationally clear**: `getEffectDisplay()` provides human-readable descriptions
- **Visually layered**: Effects stack and combine in ordered layers
- **Performance-conscious**: SVG string concatenation, CSS animations, capped particle counts
- **Deterministic**: Same effect data always produces same visual

## Common Gotcha

`ReactionCache.effects` is typed `list[str]` but stores dicts via `effect.model_dump()`. Cache reads return raw dicts, not typed Pydantic models. Frontend handles dicts fine. Backend code expecting typed Effect objects from cache needs manual deserialization.
