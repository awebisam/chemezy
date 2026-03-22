---
name: svg-artist
description: >
  Use when creating or modifying SVG symbols in the effect sprite sheet, designing CSS keyframe
  animations for chemical effects, crafting visual representations of chemical phenomena, or
  optimizing SVG paths. Trigger when the user mentions sprites, symbols, animations, keyframes,
  bubbles, vapor, smoke, foam, crystals, sparks, shimmer, glow, spill puddles, or any visual
  asset work for the beaker scene.
---

# Chemezy SVG Art & Animation

Hand-crafted SVG symbols and CSS animations that bring chemical reactions to life in a 2D beaker scene.

## Sprite Sheet: `static/svg/effect-sprites.svg`

A single SVG file containing reusable `<symbol>` elements. Referenced via `<use href="/static/svg/effect-sprites.svg#symbol-id">` in JS-generated SVG strings.

### Current Symbols

| Symbol ID | viewBox | Elements | Purpose |
|-----------|---------|----------|---------|
| `bubble-cluster` | `0 0 80 80` | 5 circles, varying r/opacity | Gas bubbles rising |
| `vapor-plume` | `0 0 100 100` | Single organic path | Steam/vapor wisps |
| `smoke-plume` | `0 0 100 100` | Single cloud path | Smoke clouds |
| `ray-burst` | `0 0 120 120` | 8 lines radiating from center | Light emission rays |
| `spark-arc` | `0 0 100 100` | Single arc path | Electrical/thermal sparks |
| `foam-cap` | `0 0 160 60` | Cloud-like path, wide aspect | Foam layer on liquid surface |
| `spill-puddle` | `0 0 200 60` | Blob path, wide aspect | Material overflow puddle |
| `crystal-shard` | `0 0 60 90` | Faceted polygon + highlight stroke | Solid crystalline formation |
| `shimmer-swipe` | `0 0 140 40` | Wave path, wide aspect | Aqueous/liquid shimmer band |

### Symbol Authoring Rules

1. **`currentColor` only** — every `fill` and `stroke` must use `currentColor`. Tinting happens via the CSS `color` property on the `<use>` element. Never hardcode colors except `white` for internal highlights.

2. **Opacity layering** — use `opacity` attributes on child elements to create depth:
   - Background/diffuse: `0.14–0.42`
   - Midground: `0.42–0.72`
   - Foreground/crisp: `0.72–0.92`

3. **Tight viewBox** — size the viewBox to tightly fit the content. The `<use>` element controls placement and scale via `x`, `y`, `width`, `height`.

4. **Hand-optimized paths** — write path data manually or clean up editor output aggressively:
   - Use relative commands (`c`, `s`, `l`) where they save bytes
   - Round coordinates to integers when possible
   - Remove redundant points that don't affect the curve visually
   - Prefer `Z` to close paths rather than repeating the start point

5. **Naming** — kebab-case IDs: `noun-noun` or `adjective-noun` (e.g., `bubble-cluster`, `crystal-shard`)

6. **No transforms on the `<symbol>` root** — transforms belong on child elements or on the `<use>` call site

### Anatomy of a Good Symbol

```svg
<symbol id="drip-trail" viewBox="0 0 40 120">
  <!-- Background diffuse element -->
  <ellipse cx="20" cy="100" rx="14" ry="6" fill="currentColor" opacity="0.28" />
  <!-- Mid element -->
  <path d="M20 8c-8 20-12 40-8 60 2 10 6 18 8 24 2-6 6-14 8-24 4-20 0-40-8-60Z"
        fill="currentColor" opacity="0.68" />
  <!-- Highlight (white allowed for internal specular) -->
  <path d="M20 14c-4 16-6 30-4 44" stroke="white" stroke-opacity="0.3"
        stroke-width="2" fill="none" />
</symbol>
```

## Animation Sheet: `@keyframes` in `static/css/app.css`

All effect animations live at the bottom of `app.css`, after all layout/component styles.

### Current Animations

| Keyframe | Properties | Pattern | Used By |
|----------|------------|---------|---------|
| `bubbleRise` | translateY, scale, opacity | Rise + shrink + fade | gas_production (bubbles) |
| `vaporDrift` | translate, scale, opacity | Float up + swell | gas_production (vapor/smoke) |
| `foamBob` | translateY | Gentle vertical bob | foam_production |
| `pulseLight` | scale, opacity | Breathe in/out | light_emission |
| `heatRipple` | opacity | Slow pulse | temperature_change (hot) |
| `frostTwinkle` | opacity, translateY | Pulse + slight rise | temperature_change (cold) |
| `spillSlide` | opacity | Slow reveal | spill (drip) |
| `puddlePulse` | scale | Subtle breathe | spill (puddle) |
| `zapPulse` | opacity | Sharp pulse | state_change (plasma) |
| `surfaceBob` | translateY | Tiny vertical bob | state_change (liquid) |
| `shimmerDrift` | translateX | Horizontal sway | state_change (aqueous), texture |
| `gooeyDrift` | translateX, scale | Sway + stretch | texture_change |
| `crystalBlink` | opacity | Slow fade pulse | texture_change (grainy), state_change (solid) |
| `beakerWobble` | rotate | Gentle rock | beaker container (reacting) |
| `settleBeaker` | scaleY | Micro squash | beaker container (volume) |

### Animation Design Rules

1. **Seamless loops** — `0%` and `100%` keyframes must match exactly. Use `0%, 100% { ... }` syntax.

   Exception: `bubbleRise` is a one-shot (0% to 100% with `iteration-count` on the element). Non-looping animations are rare — default to loops.

2. **Subtle motion** — chemical effects are background ambiance, not the main event:
   - Translations: `3–20px` range
   - Scale: `0.9–1.1` range (never more than 10% deviation)
   - Rotation: under `2deg`
   - Opacity: oscillate within a sub-range, never 0→1 full swing

3. **Staggering via `animation-delay`** — the JS applies `animation-delay` on individual `<use>` elements to offset identical animations. Design animations that look good when multiple instances run at different phases.

4. **Duration ranges** — animations are applied in JS with `animation: keyframeName ${duration}s ease-in-out infinite`. Typical durations:
   - Fast/energetic (sparks, plasma): `0.8–2s`
   - Medium (bubbles, vapor): `2–6s`
   - Slow/ambient (shimmer, glow, foam): `4–18s`

5. **Easing** — `ease-in-out` is the default. Only override if the effect demands it (e.g., `linear` for constant drift).

6. **Property constraints** — only animate `transform` and `opacity`. These are compositor-friendly and won't cause layout thrashing. Never animate `fill`, `stroke`, `width`, `height`, or `d`.

### Naming Convention

`camelCase` matching the chemical phenomenon:
- Physical motion: `bubbleRise`, `vaporDrift`, `foamBob`, `surfaceBob`
- Light/energy: `pulseLight`, `zapPulse`, `heatRipple`, `frostTwinkle`
- Surface/texture: `shimmerDrift`, `gooeyDrift`, `crystalBlink`
- Container: `beakerWobble`, `settleBeaker`
- Spill: `spillSlide`, `puddlePulse`

## How Sprites Connect to JS

`beaker-scene.js` references sprites via template literal SVG strings:

```javascript
`<use href="${SPRITE_PATH}#symbol-id"
      x="${x}" y="${y}" width="${w}" height="${h}"
      style="color:${color};opacity:${opacity};animation:keyframeName ${duration}s ease-in-out infinite;"
/>`
```

Key facts:
- `SPRITE_PATH` = `"/static/svg/effect-sprites.svg"`
- Color tinting via inline `color` style (read by `currentColor`)
- Animation applied via inline `style` with duration from effect data
- Position/scale via `x`, `y`, `width`, `height` attributes
- Multiple instances with `animation-delay` for stagger

## Beaker Scene Geometry

The beaker SVG uses viewBox `0 0 320 440`:
- Beaker glass body: roughly `x:60–260, y:124–314`
- Liquid fills from bottom (`y:314`) upward
- `liquidTop` = `314 - liquidHeight` (dynamic based on reactant volume)
- Effects render inside a `clip-path` matching the beaker interior
- Spill effects render OUTSIDE the clip-path, below the beaker rim

When positioning sprites, stay within these bounds:
- **Inside liquid**: `x:70–250`, `y:liquidTop–310`
- **Above liquid surface**: `y:liquidTop-40` to `y:liquidTop`
- **Below beaker (spill)**: `y:320+`

## Design Philosophy

- **Scientifically suggestive** — effects should evoke real phenomena without being photorealistic
- **Layered depth** — multiple opacity levels create the illusion of volume in 2D
- **Performance** — SVG string concat, CSS-only animation, capped particle counts (2–8 per effect)
- **Deterministic** — same effect data always produces the same visual. No randomness in sprites or keyframes (stagger comes from JS `animation-delay`)
