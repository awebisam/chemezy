import { getEnvironment } from "../config/environments.js";
import { clamp, escapeHtml, safeColor } from "../utils/formatters.js";
import {
  getCombinedVolumeFactor,
  getNetTemperatureDelta,
  getPrimaryState,
  getPrimaryTexture,
  getSceneMetrics,
  groupEffects,
  normalizeEffects,
} from "../utils/effects.js";
import {
  BEAKER_VIEWBOX,
  CLIP_PATH,
  buildBeakerBackdrop,
  buildBeakerForeground,
  buildBeakerGlassCore,
  buildBeakerHud,
} from "./lab-svg/beaker-shell.js";

const SPRITE_PATH = "/static/svg/effect-sprites.svg";

export function buildBeakerScene({
  environment,
  reactants = [],
  products = [],
  effects = [],
  isReacting = false,
  size = "stage",
  sceneId = "main",
} = {}) {
  const env =
    typeof environment === "string" || !environment
      ? getEnvironment(environment)
      : environment;
  const normalizedEffects = normalizeEffects(effects);
  const groupedEffects = groupEffects(normalizedEffects);
  const metrics = getSceneMetrics({
    reactants,
    products,
    effects: normalizedEffects,
  });
  const liquidHeight = Math.round(metrics.liquidLevel * 190);
  const liquidTop = 314 - liquidHeight;
  const temperatureDelta = getNetTemperatureDelta(normalizedEffects);
  const primaryState = getPrimaryState(normalizedEffects);
  const primaryTexture = getPrimaryTexture(normalizedEffects);
  const volumeFactor = getCombinedVolumeFactor(normalizedEffects);
  const sceneClasses = [
    "beaker-svg",
    getSceneSizeClass(size),
    isReacting ? "beaker--reacting" : "",
    volumeFactor > 1.08 ? "beaker--swelling" : "",
    volumeFactor < 0.94 ? "beaker--shrinking" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const clipId = `${sceneId}-clip`;
  const gradientId = `${sceneId}-liquid-gradient`;
  const glowId = `${sceneId}-glow-gradient`;
  const environmentName = escapeHtml(env.shortLabel || env.name);
  const effectCount = normalizedEffects.length;
  const formulas = reactants.length
    ? reactants
        .map((reactant) => escapeHtml(reactant.molecular_formula || "Mix"))
        .slice(0, 3)
        .join(" + ")
    : "Drop compounds here";
  const liquidTone = getLiquidTone({
    environment: env,
    temperatureDelta,
    texture: primaryTexture,
  });

  return `
    <svg class="${sceneClasses}" viewBox="${BEAKER_VIEWBOX}" role="img" aria-label="Chemezy beaker scene">
      <defs>
        <clipPath id="${clipId}">
          <path d="${CLIP_PATH}" />
        </clipPath>
        <linearGradient id="${gradientId}" x1="0%" y1="100%" x2="0%" y2="0%">
          <stop offset="0%" stop-color="${liquidTone.bottom}" />
          <stop offset="100%" stop-color="${liquidTone.top}" />
        </linearGradient>
        <radialGradient id="${glowId}" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stop-color="${liquidTone.glow}" stop-opacity="0.48" />
          <stop offset="100%" stop-color="${liquidTone.glow}" stop-opacity="0" />
        </radialGradient>
      </defs>

      ${buildBeakerBackdrop({
        glowId,
        panelFill: "#ffffff",
        shadowFill: env.colors.accentSoft,
      })}

      ${renderSpillLayer(groupedEffects.spill, liquidTop)}

      <g class="glass-core">
        ${buildBeakerGlassCore({
          strokeColor: env.colors.accent,
          rimFill: env.colors.panel,
          rimHighlight: "#d7ebff",
        })}
      </g>

      <g clip-path="url(#${clipId})">
        <rect x="92" y="${liquidTop}" width="176" height="${Math.max(liquidHeight, 8)}" fill="url(#${gradientId})" class="liquid-body" />
        <path
          d="M92 ${liquidTop + 14} C118 ${liquidTop - 6}, 138 ${liquidTop + 6}, 166 ${liquidTop - 4} C194 ${liquidTop - 14}, 222 ${liquidTop + 10}, 268 ${liquidTop + 4} V344 H92 Z"
          fill="${liquidTone.surface}"
          opacity="0.65"
          class="liquid-surface"
        />
        ${renderVolumeHints(volumeFactor, liquidTop)}
        ${renderStateLayer(groupedEffects.state_change, liquidTop)}
        ${renderTextureLayer(groupedEffects.texture_change, liquidTop)}
        ${renderFoamLayer(groupedEffects.foam_production, liquidTop)}
        ${renderGasLayer(groupedEffects.gas_production, liquidTop)}
        ${renderTemperatureLayer(groupedEffects.temperature_change, liquidTop)}
        ${renderLightLayer(groupedEffects.light_emission)}
      </g>

      <g class="foreground-glass">
        ${buildBeakerForeground()}
      </g>

      <g class="scene-hud">
        ${buildBeakerHud({
          environmentIcon: escapeHtml(env.icon),
          environmentName,
          effectCount,
          formulas,
        })}
      </g>
    </svg>
  `;
}

function getSceneSizeClass(size) {
  switch (size) {
    case "hero":
      return "beaker-svg--hero";
    case "launcher":
      return "beaker-svg--launcher";
    case "modal":
      return "beaker-svg--modal";
    default:
      return "beaker-svg--stage";
  }
}

function getLiquidTone({ environment, temperatureDelta, texture }) {
  const baseTop = texture?.color || environment.colors.liquidB;
  const baseBottom = environment.colors.liquidA;

  if (temperatureDelta > 20) {
    return {
      top: safeColor("#ffd166", baseTop),
      bottom: safeColor("#ff7f50", baseBottom),
      surface: "#fff0cc",
      glow: "#ffd68a",
    };
  }

  if (temperatureDelta < -20) {
    return {
      top: "#b8ecff",
      bottom: "#6a8dff",
      surface: "#e8fbff",
      glow: "#9fdfff",
    };
  }

  return {
    top: safeColor(baseTop, environment.colors.liquidB),
    bottom: safeColor(baseBottom, environment.colors.liquidA),
    surface: "#ffffff",
    glow: safeColor(environment.colors.glow, "#a3d8ff"),
  };
}

function renderVolumeHints(volumeFactor, liquidTop) {
  if (Math.abs(volumeFactor - 1) < 0.06) {
    return "";
  }

  const bandY = liquidTop - (volumeFactor > 1 ? 20 : -16);
  const opacity = volumeFactor > 1 ? 0.18 : 0.12;
  return `
    <ellipse
      cx="180"
      cy="${bandY}"
      rx="${volumeFactor > 1 ? 88 : 74}"
      ry="${volumeFactor > 1 ? 18 : 12}"
      fill="#ffffff"
      opacity="${opacity}"
      class="scene-wave"
    />
  `;
}

function renderGasLayer(effects, liquidTop) {
  if (!effects.length) {
    return "";
  }

  return effects
    .map((effect, effectIndex) => {
      const count = Math.max(2, Math.round(2 + effect.intensity * 6));
      const spriteSize = 22 + effect.intensity * 26;
      return Array.from({ length: count }, (_, index) => {
        const x = 110 + ((effectIndex * 37 + index * 29) % 110);
        const y = liquidTop - 10 - (index % 3) * 12;
        const opacity = clamp(0.28 + effect.intensity * 0.42, 0.2, 0.88);
        const duration = clamp(effect.duration * (effect.preset.key === "bubbles" ? 0.7 : 1), 1, 12);
        const animationClass = effect.preset.key === "bubbles" ? "float-bubble" : "drift-vapor";
        return `
          <use
            href="${SPRITE_PATH}#${effect.preset.symbol}"
            x="${x}"
            y="${y}"
            width="${spriteSize}"
            height="${spriteSize}"
            class="${animationClass}"
            style="color:${effect.color};opacity:${opacity};animation-duration:${duration}s;animation-delay:${index * 0.24}s;"
          />
        `;
      }).join("");
    })
    .join("");
}

function renderFoamLayer(effects, liquidTop) {
  if (!effects.length) {
    return "";
  }

  return effects
    .map((effect, effectIndex) => {
      const width = clamp(130 + effect.density * 18, 132, 168);
      const height = 34 + effect.bubbleScale * 14;
      const x = 180 - width / 2;
      const y = liquidTop - 10 - effectIndex * 6;
      const opacity = clamp(0.5 + effect.density * 0.08, 0.55, 0.92);
      return `
        <use
          href="${SPRITE_PATH}#foam-cap"
          x="${x}"
          y="${y}"
          width="${width}"
          height="${height}"
          class="foam-float"
          style="color:${effect.color};opacity:${opacity};animation-duration:${clamp(effect.stability, 1.2, 12)}s;animation-delay:${effectIndex * 0.28}s;"
        />
      `;
    })
    .join("");
}

function renderLightLayer(effects) {
  if (!effects.length) {
    return "";
  }

  return effects
    .map((effect, effectIndex) => {
      const radius = 58 + effect.radius * 12;
      const opacity = clamp(0.12 + effect.intensity * 0.34, 0.12, 0.58);
      return `
        <circle
          cx="180"
          cy="204"
          r="${radius}"
          fill="${effect.color}"
          opacity="${opacity}"
          class="pulse-light"
          style="animation-duration:${clamp(effect.duration, 1, 10)}s;animation-delay:${effectIndex * 0.18}s;"
        />
        <use
          href="${SPRITE_PATH}#ray-burst"
          x="${95 - effect.radius * 4}"
          y="${118 - effect.radius * 4}"
          width="${170 + effect.radius * 8}"
          height="${170 + effect.radius * 8}"
          class="pulse-light"
          style="color:${effect.color};opacity:${clamp(0.18 + effect.intensity * 0.26, 0.18, 0.6)};animation-duration:${clamp(effect.duration * 0.9, 1, 10)}s;"
        />
      `;
    })
    .join("");
}

function renderSpillLayer(effects, liquidTop) {
  if (!effects.length) {
    return "";
  }

  const maxAmount = Math.max(...effects.map((effect) => effect.amount_percentage));
  const maxSpread = Math.max(...effects.map((effect) => effect.spread_radius));
  const width = 150 + maxSpread * 18;
  const x = 180 - width / 2;
  const opacity = clamp(0.16 + maxAmount * 0.55, 0.18, 0.72);
  const puddleColor = effects[0].color || "#ff9f68";

  return `
    <path
      d="M246 ${liquidTop - 6} C260 ${liquidTop + 14}, 274 ${liquidTop + 40}, 282 332"
      fill="none"
      stroke="${puddleColor}"
      stroke-width="${6 + maxAmount * 8}"
      stroke-linecap="round"
      opacity="${opacity}"
      class="spill-flow"
      style="animation-duration:${2.8 + maxAmount * 2}s;"
    />
    <use
      href="${SPRITE_PATH}#spill-puddle"
      x="${x}"
      y="328"
      width="${width}"
      height="52"
      class="puddle-pulse"
      style="color:${puddleColor};opacity:${opacity};"
    />
  `;
}

function renderStateLayer(effects, liquidTop) {
  if (!effects.length) {
    return "";
  }

  return effects
    .map((effect, effectIndex) => {
      switch (effect.statePreset) {
        case "solid":
          return renderSolidState(effectIndex, liquidTop);
        case "gas":
          return renderGasState(effectIndex, liquidTop);
        case "plasma":
          return renderPlasmaState(effectIndex, liquidTop);
        case "aqueous":
          return renderAqueousState(effectIndex, liquidTop);
        default:
          return renderLiquidState(effectIndex, liquidTop);
      }
    })
    .join("");
}

function renderSolidState(effectIndex, liquidTop) {
  return Array.from({ length: 5 }, (_, index) => {
    const x = 102 + index * 30 + (effectIndex % 2) * 6;
    const y = liquidTop + 10 + (index % 2) * 5;
    return `
      <use
        href="${SPRITE_PATH}#crystal-shard"
        x="${x}"
        y="${y}"
        width="26"
        height="38"
        class="crystal-gleam"
        style="color:#eef6ff;opacity:0.42;animation-delay:${index * 0.22}s;"
      />
    `;
  }).join("");
}

function renderGasState(effectIndex, liquidTop) {
  return `
    <use
      href="${SPRITE_PATH}#vapor-plume"
      x="116"
      y="${liquidTop - 36 - effectIndex * 8}"
      width="48"
      height="48"
      class="drift-vapor"
      style="color:#f8fbff;opacity:0.3;animation-duration:5.2s;"
    />
    <use
      href="${SPRITE_PATH}#vapor-plume"
      x="188"
      y="${liquidTop - 42 - effectIndex * 8}"
      width="56"
      height="56"
      class="drift-vapor"
      style="color:#eefbff;opacity:0.22;animation-duration:6.1s;animation-delay:0.4s;"
    />
  `;
}

function renderPlasmaState(effectIndex, liquidTop) {
  return `
    <circle cx="180" cy="${liquidTop + 70}" r="68" fill="#c7afff" opacity="0.12" class="pulse-light" />
    <use
      href="${SPRITE_PATH}#spark-arc"
      x="120"
      y="${liquidTop + 20}"
      width="64"
      height="64"
      class="arc-zap"
      style="color:#fff1a8;opacity:0.8;animation-delay:${effectIndex * 0.18}s;"
    />
    <use
      href="${SPRITE_PATH}#spark-arc"
      x="176"
      y="${liquidTop + 56}"
      width="58"
      height="58"
      class="arc-zap"
      style="color:#9a7fff;opacity:0.68;animation-delay:${0.3 + effectIndex * 0.12}s;"
    />
  `;
}

function renderAqueousState(effectIndex, liquidTop) {
  return `
    <use
      href="${SPRITE_PATH}#shimmer-swipe"
      x="100"
      y="${liquidTop + 22 + effectIndex * 6}"
      width="150"
      height="36"
      class="shimmer-drift"
      style="color:#ffffff;opacity:0.26;"
    />
    <use
      href="${SPRITE_PATH}#shimmer-swipe"
      x="112"
      y="${liquidTop + 76 + effectIndex * 8}"
      width="132"
      height="30"
      class="shimmer-drift"
      style="color:#dffcff;opacity:0.18;animation-delay:0.3s;"
    />
  `;
}

function renderLiquidState(effectIndex, liquidTop) {
  return `
    <ellipse
      cx="180"
      cy="${liquidTop + 18 + effectIndex * 3}"
      rx="76"
      ry="10"
      fill="#ffffff"
      opacity="0.18"
      class="scene-wave"
    />
  `;
}

function renderTextureLayer(effects, liquidTop) {
  if (!effects.length) {
    return "";
  }

  return effects
    .map((effect, effectIndex) => {
      const opacity = clamp(0.18 + effect.viscosity * 0.36, 0.18, 0.72);
      if (effect.texturePreset === "grainy") {
        return Array.from({ length: 6 }, (_, index) => {
          const x = 114 + (index * 23) % 104;
          const y = liquidTop + 20 + (index % 3) * 34 + effectIndex * 5;
          return `
            <use
              href="${SPRITE_PATH}#crystal-shard"
              x="${x}"
              y="${y}"
              width="18"
              height="22"
              class="crystal-gleam"
              style="color:${effect.color};opacity:${opacity * 0.45};animation-delay:${index * 0.2}s;"
            />
          `;
        }).join("");
      }

      return `
        <use
          href="${SPRITE_PATH}#shimmer-swipe"
          x="101"
          y="${liquidTop + 24 + effectIndex * 12}"
          width="148"
          height="36"
          class="${effect.texturePreset === "gooey" ? "gooey-drift" : "shimmer-drift"}"
          style="color:${effect.color};opacity:${opacity};animation-duration:${3.5 + effect.viscosity * 3}s;"
        />
        <use
          href="${SPRITE_PATH}#shimmer-swipe"
          x="109"
          y="${liquidTop + 96 + effectIndex * 10}"
          width="134"
          height="30"
          class="${effect.texturePreset === "thick" ? "gooey-drift" : "shimmer-drift"}"
          style="color:${effect.color};opacity:${opacity * 0.68};animation-duration:${4.3 + effect.viscosity * 3}s;animation-delay:0.3s;"
        />
      `;
    })
    .join("");
}

function renderTemperatureLayer(effects, liquidTop) {
  if (!effects.length) {
    return "";
  }

  const netDelta = effects.reduce((total, effect) => total + effect.delta_celsius, 0);
  if (netDelta >= 0) {
    const intensity = clamp(netDelta / 80, 0.2, 1);
    return `
      <path
        d="M118 ${liquidTop + 120} C132 ${liquidTop + 92}, 150 ${liquidTop + 94}, 164 ${liquidTop + 68} C176 ${liquidTop + 46}, 194 ${liquidTop + 46}, 210 ${liquidTop + 20}"
        fill="none"
        stroke="#ff934f"
        stroke-width="${3 + intensity * 3}"
        stroke-linecap="round"
        opacity="${0.28 + intensity * 0.36}"
        class="warm-wave"
      />
      <use href="${SPRITE_PATH}#spark-arc" x="132" y="${liquidTop + 24}" width="56" height="56" class="spark-arc" style="color:#ffd166;opacity:${0.44 + intensity * 0.28};" />
      <use href="${SPRITE_PATH}#spark-arc" x="184" y="${liquidTop + 60}" width="42" height="42" class="spark-arc" style="color:#ff7f50;opacity:${0.3 + intensity * 0.28};animation-delay:0.25s;" />
    `;
  }

  const coolIntensity = clamp(Math.abs(netDelta) / 80, 0.2, 1);
  return Array.from({ length: 7 }, (_, index) => {
    const x = 112 + (index * 22) % 122;
    const y = liquidTop + 22 + (index % 4) * 26;
    const radius = 3 + (index % 2);
    return `
      <circle
        cx="${x}"
        cy="${y}"
        r="${radius}"
        fill="#dbf4ff"
        opacity="${0.22 + coolIntensity * 0.28}"
        class="cool-speck"
        style="animation-delay:${index * 0.18}s;"
      />
    `;
  }).join("");
}
