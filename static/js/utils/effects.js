import {
  clamp,
  formatPercent,
  formatSignedNumber,
  safeColor,
  titleCase,
} from "./formatters.js";

const DEFAULT_EFFECT_COLOR = "#5c7cfa";
const GAS_SYMBOLS = {
  bubbles: "bubble-cluster",
  vapor: "vapor-plume",
  smoke: "smoke-plume",
};

const TEXTURE_PRESETS = {
  gooey: "gooey",
  slimy: "gooey",
  viscous: "thick",
  sticky: "thick",
  silky: "smooth",
  chalky: "grainy",
  crystalline: "grainy",
};

const STATE_PRESETS = {
  solid: "solid",
  liquid: "liquid",
  gas: "gas",
  plasma: "plasma",
  aqueous: "aqueous",
};

const BUBBLE_SCALE = {
  small: 0.75,
  medium: 1,
  large: 1.35,
};

export function normalizeEffects(effects = []) {
  return effects
    .filter(Boolean)
    .map((effect, index) => normalizeEffect(effect, index));
}

export function groupEffects(effects = []) {
  const groups = {
    gas_production: [],
    light_emission: [],
    volume_change: [],
    spill: [],
    state_change: [],
    temperature_change: [],
    texture_change: [],
    foam_production: [],
  };

  effects.forEach((effect) => {
    if (groups[effect.effect_type]) {
      groups[effect.effect_type].push(effect);
    }
  });

  return groups;
}

export function getPrimaryState(effects = []) {
  return groupEffects(effects).state_change.at(-1) || null;
}

export function getPrimaryTexture(effects = []) {
  return groupEffects(effects).texture_change.at(-1) || null;
}

export function getNetTemperatureDelta(effects = []) {
  return groupEffects(effects).temperature_change.reduce(
    (total, effect) => total + effect.delta_celsius,
    0,
  );
}

export function getCombinedVolumeFactor(effects = []) {
  const factor = groupEffects(effects).volume_change.reduce(
    (total, effect) => total * effect.factor,
    1,
  );

  return clamp(factor, 0.55, 1.7);
}

export function getSceneMetrics({ reactants = [], products = [], effects = [] }) {
  const normalized = Array.isArray(effects) && effects.length && effects[0].effect_type
    ? effects
    : normalizeEffects(effects);
  const volumeFactor = getCombinedVolumeFactor(normalized);
  const reactantLoad = 0.26 + reactants.length * 0.08;
  const productBonus = Math.min(products.length * 0.035, 0.14);

  return {
    liquidLevel: clamp((reactantLoad + productBonus) * volumeFactor, 0.2, 0.84),
    volumeFactor,
    temperatureDelta: getNetTemperatureDelta(normalized),
  };
}

export function getGasPreset(gasType) {
  const key = String(gasType || "vapor").toLowerCase().trim();
  return {
    key,
    symbol: GAS_SYMBOLS[key] || GAS_SYMBOLS.vapor,
  };
}

export function getTexturePreset(textureType) {
  const key = String(textureType || "viscous").toLowerCase().trim();
  return TEXTURE_PRESETS[key] || "smooth";
}

export function getStatePreset(finalState) {
  const key = String(finalState || "liquid").toLowerCase().trim();
  return STATE_PRESETS[key] || "liquid";
}

export function getBubbleScale(size) {
  return BUBBLE_SCALE[String(size || "medium").toLowerCase()] || 1;
}

export function getEffectDisplay(effect) {
  switch (effect.effect_type) {
    case "gas_production":
      return {
        title: "Gas Production",
        tone: "sky",
        description:
          effect.preset.key === "bubbles"
            ? "Fizzing pockets escape from the mix."
            : effect.preset.key === "smoke"
              ? "Dense clouds roll upward from the surface."
              : "Soft vapor drifts out of the beaker.",
        facts: [
          { label: "Type", value: titleCase(effect.gas_type) },
          { label: "Intensity", value: formatPercent(effect.intensity) },
          { label: "Duration", value: `${effect.duration.toFixed(1)}s` },
        ],
      };
    case "light_emission":
      return {
        title: "Light Emission",
        tone: "gold",
        description: "The reaction glows and pulses with released energy.",
        facts: [
          { label: "Intensity", value: formatPercent(effect.intensity) },
          { label: "Radius", value: `${effect.radius.toFixed(1)}m` },
          { label: "Duration", value: `${effect.duration.toFixed(1)}s` },
        ],
      };
    case "volume_change":
      return {
        title: "Volume Change",
        tone: "violet",
        description:
          effect.factor >= 1
            ? "The mixture expands and pushes upward."
            : "The mixture settles into a smaller volume.",
        facts: [{ label: "Factor", value: `${effect.factor.toFixed(2)}x` }],
      };
    case "spill":
      return {
        title: "Spill",
        tone: "coral",
        description: "Material slips over the rim and spreads around the base.",
        facts: [
          { label: "Amount", value: formatPercent(effect.amount_percentage) },
          { label: "Spread", value: `${effect.spread_radius.toFixed(1)}m` },
        ],
      };
    case "state_change":
      return {
        title: "State Change",
        tone: "mint",
        description: "A product changes how it behaves in the beaker.",
        facts: [
          { label: "Product", value: `#${effect.product_chemical_id}` },
          { label: "Final State", value: titleCase(effect.final_state) },
        ],
      };
    case "temperature_change":
      return {
        title: "Temperature Shift",
        tone: effect.delta_celsius >= 0 ? "coral" : "sky",
        description:
          effect.delta_celsius >= 0
            ? "Heat ripples outward from the reaction."
            : "Cooling haze settles around the mixture.",
        facts: [{ label: "Delta", value: formatSignedNumber(effect.delta_celsius, 0, "°C") }],
      };
    case "texture_change":
      return {
        title: "Texture Change",
        tone: "violet",
        description: "The surface takes on a new feel and motion pattern.",
        facts: [
          { label: "Texture", value: titleCase(effect.texture_type) },
          { label: "Viscosity", value: formatPercent(effect.viscosity) },
          { label: "Product", value: `#${effect.product_chemical_id}` },
        ],
      };
    case "foam_production":
      return {
        title: "Foam Production",
        tone: "mint",
        description: "A bubbly cap forms and lingers over the surface.",
        facts: [
          { label: "Density", value: effect.density.toFixed(1) },
          { label: "Bubble Size", value: titleCase(effect.bubble_size) },
          { label: "Stability", value: `${effect.stability.toFixed(1)}s` },
        ],
      };
    default:
      return {
        title: titleCase(effect.effect_type),
        tone: "sky",
        description: "This effect is supported as data, even if it uses a fallback visual.",
        facts: [],
      };
  }
}

export const PREVIEW_REACTION = {
  environment: "Pure Oxygen",
  reactants: [
    { molecular_formula: "CuSO4" },
    { molecular_formula: "NH3" },
  ],
  products: [
    { molecular_formula: "Complex", common_name: "Bright Copper Complex", quantity: 1.0 },
  ],
  effects: normalizeEffects([
    {
      effect_type: "gas_production",
      gas_type: "vapor",
      color: "#a855f7",
      intensity: 0.68,
      duration: 4.2,
    },
    {
      effect_type: "light_emission",
      color: "#ffd166",
      intensity: 0.72,
      radius: 2.4,
      duration: 3.2,
    },
    {
      effect_type: "foam_production",
      color: "#f8fafc",
      density: 1.5,
      bubble_size: "medium",
      stability: 4.6,
    },
    {
      effect_type: "temperature_change",
      delta_celsius: 42,
    },
    {
      effect_type: "texture_change",
      product_chemical_id: 1,
      texture_type: "silky",
      color: "#9b8cff",
      viscosity: 0.35,
    },
  ]),
};

function normalizeEffect(effect, index) {
  switch (effect.effect_type) {
    case "gas_production":
      return {
        ...effect,
        _key: `gas-${index}`,
        color: safeColor(effect.color, "#7c98ff"),
        intensity: clamp(effect.intensity, 0.08, 1),
        duration: clamp(effect.duration, 0.8, 18),
        preset: getGasPreset(effect.gas_type),
      };
    case "light_emission":
      return {
        ...effect,
        _key: `light-${index}`,
        color: safeColor(effect.color, "#ffd166"),
        intensity: clamp(effect.intensity, 0.08, 1),
        radius: clamp(effect.radius, 0.3, 6),
        duration: clamp(effect.duration, 0.8, 18),
      };
    case "volume_change":
      return {
        ...effect,
        _key: `volume-${index}`,
        factor: clamp(effect.factor, 0.25, 2.5),
      };
    case "spill":
      return {
        ...effect,
        _key: `spill-${index}`,
        amount_percentage: clamp(effect.amount_percentage, 0, 1),
        spread_radius: clamp(effect.spread_radius, 0.15, 6),
      };
    case "state_change":
      return {
        ...effect,
        _key: `state-${index}`,
        statePreset: getStatePreset(effect.final_state),
      };
    case "temperature_change":
      return {
        ...effect,
        _key: `temperature-${index}`,
        delta_celsius: clamp(effect.delta_celsius, -250, 250),
      };
    case "texture_change":
      return {
        ...effect,
        _key: `texture-${index}`,
        color: safeColor(effect.color, "#8b5cf6"),
        viscosity: clamp(effect.viscosity, 0, 1),
        texturePreset: getTexturePreset(effect.texture_type),
      };
    case "foam_production":
      return {
        ...effect,
        _key: `foam-${index}`,
        color: safeColor(effect.color, "#f8fafc"),
        density: clamp(effect.density, 0.2, 5),
        stability: clamp(effect.stability, 0.8, 20),
        bubble_size: String(effect.bubble_size || "medium").toLowerCase(),
        bubbleScale: getBubbleScale(effect.bubble_size),
      };
    default:
      return {
        ...effect,
        _key: `effect-${index}`,
        color: safeColor(effect.color, DEFAULT_EFFECT_COLOR),
      };
  }
}
