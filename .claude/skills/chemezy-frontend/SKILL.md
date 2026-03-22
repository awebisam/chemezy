---
name: chemezy-frontend
description: >
  Use when working on the Chemezy browser UI: Alpine.js components, the app store, SVG beaker
  rendering, effect animations, CSS theming, the compound deck, lab stage, modals, drag-and-drop,
  the landing page, notifications, or any HTML/JS/CSS in the Chemezy repo. Trigger whenever the
  user mentions UI, layout, animation, responsive design, mobile tabs, the playground modal, beaker
  visuals, compound cards, or wants to change how anything looks or behaves in the browser.
---

# Chemezy Frontend Development

No-build Alpine.js + vanilla ES modules UI serving as a thin client to the FastAPI backend. No independent chemistry logic.

## Architecture: No Build Step

- `index.html` at repo root -> served at `/` via `FileResponse`
- `static/` directory -> mounted at `/static/*` via `StaticFiles`
- Alpine.js from CDN (`alpinejs@3.14.9`)
- All JS are ES modules imported directly in the browser
- **No Node.js, no Vite, no webpack, no npm**

## File Map

```
index.html                              # Full HTML shell with Alpine.js directives
static/
├── css/app.css                         # All styles, animations, responsive breakpoints
├── js/
│   ├── main.js                         # Boot: imports Alpine, registers all components
│   ├── api.js                          # createApiClient() — fetch wrapper with auth
│   ├── config/environments.js          # Environment definitions (colors, icons, labels)
│   ├── utils/
│   │   ├── effects.js                  # Effect normalization, grouping, display metadata
│   │   └── formatters.js              # clamp, escapeHtml, safeColor, titleCase, etc.
│   └── components/
│       ├── app-store.js               # Alpine.store("app") — THE central state object
│       ├── landing.js                 # Pre-auth landing hero with preview beaker
│       ├── lab-stage.js               # Main lab area (playground modal content)
│       ├── beaker-scene.js            # SVG beaker renderer — the visual heart
│       ├── inventory-composer.js      # Compound deck + drag/drop + add chemical form
│       ├── player-sidebar.js          # Awards, stats, leaderboard sidebar
│       ├── auth-modal.js             # Login/register modal
│       ├── debug-modal.js            # Admin debug panel
│       ├── notifications.js          # Toast + award notification panel
│       ├── effect-inspector.js       # Effect detail cards
│       └── lab-svg/
│           ├── beaker-shell.js       # Core SVG paths, glass, rim, HUD
│           ├── compound-deck.js      # Compound card SVG rendering
│           └── test-tube.js          # Test tube SVG elements
├── svg/
│   ├── effect-sprites.svg            # Reusable SVG sprite sheet
│   └── favicon.svg
```

## Component Registration Pattern

```javascript
// Component file:
export function registerLabStage(Alpine) {
  Alpine.data("labStage", () => ({
    get app() { return Alpine.store("app"); },
    // ... component logic
  }));
}

// main.js:
import { registerLabStage } from "./components/lab-stage.js";
registerLabStage(Alpine);

// HTML:
// <div x-data="labStage"> ... </div>
```

New components must be:
1. ES module with a `register*` export
2. Imported and called in `main.js`
3. Referenced via `x-data="componentName"` in `index.html`

## The App Store (Central State)

`Alpine.store("app")` in `app-store.js` is the single source of truth for all UI state.

| Category | Fields |
|----------|--------|
| Auth | `isAuthenticated`, `authToken`, `username`, `currentUser` |
| UI | `showLoginModal`, `showPlaygroundModal`, `showWorldFirstEffect`, `activeMobileTab`, `loading`, `isDragging`, `isReacting` |
| Data | `chemicals[]`, `reactants[]`, `benchProducts[]`, `lastReaction`, `myAwards[]`, `leaderboard[]`, `reactionStats`, `dashboardStats`, `awardNotifications[]` |
| Environment | `selectedEnvironment`, `selectedCatalyst`, `environments[]` |

### Key Store Methods
- `init()` — checks localStorage for token, loads data if authenticated
- `loadInitialData()` — parallel fetches: chemicals, awards, leaderboard, stats, notifications
- `handleLogin()` / `logout()` — auth flow with token in localStorage
- `addChemical()` — POST to `/chemicals/`
- `loadReactant(chemical)` — add to reaction chamber
- `runReaction()` — POST to `/reactions/react`, update bench, check world-first
- `startDrag(event, chemical)` / `handleDrop(event)` — drag-and-drop
- `pushToast(title, type, message)` — notifications with auto-dismiss

## The Beaker Scene (SVG Rendering)

`buildBeakerScene()` takes reaction data and returns an SVG string. Regenerated from data each time (not live canvas).

Rendering pipeline:
1. Normalize effects via `normalizeEffects()` (clamps values, adds presets)
2. Group by type via `groupEffects()`
3. Calculate scene metrics (liquid level, volume factor, temperature delta)
4. Determine liquid colors from environment + temperature + texture
5. Render layers: backdrop -> spill -> glass core -> (clipped: liquid body -> effects) -> foreground glass -> HUD

Effect layers render inside a `clip-path` matching the beaker shape.

### SVG Sprite System
`effect-sprites.svg` contains `<symbol>` elements referenced via `<use href="...#symbol-id">`:
`bubble-cluster`, `vapor-plume`, `smoke-plume`, `foam-cap`, `crystal-shard`, `spark-arc`, `shimmer-swipe`, `ray-burst`, `spill-puddle`

## CSS Architecture (`app.css`)

Single file, no preprocessor:
- CSS custom properties for theming
- Responsive grid with mobile breakpoint at `1080px`
- Modal system for playground overlay
- Beaker sizing: `beaker-svg--hero`, `beaker-svg--launcher`, `beaker-svg--modal`, `beaker-svg--stage`
- Animation keyframes for all effect types
- Toast notification animations

## UI Flow

1. **Unauthenticated**: Landing page with preview beaker (`PREVIEW_REACTION`)
2. **Login**: Modal -> JWT token in localStorage
3. **Authenticated**: Launcher panel -> "Enter Lab" opens playground modal
4. **Playground Modal**: Compound deck (top), beaker (center), sidebar (right)
5. **Mobile** (`<1080px`): Tab-based layout (`activeMobileTab`: `lab`, `inventory`, `profile`)

## API Client

`createApiClient({ baseUrl, getToken, onUnauthorized })` in `api.js`. All calls go through `store.api.request(endpoint, options)`. Auto-sets JSON content type, attaches Bearer token, calls `onUnauthorized` on 401.

## Key Patterns

- All state mutations go through the app store, never local component state for shared data
- SVG rendering is string concatenation (template literals), not DOM manipulation
- `enrichChemicalRecord()` hydrates product/bench items from the chemical catalog
- `uniqBy()` deduplicates arrays by key function
- Toast notifications auto-dismiss after 4200ms
- World-first celebration: `showWorldFirstEffect = true` for 2400ms with toast
