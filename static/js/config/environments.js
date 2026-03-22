export const ENVIRONMENTS = [
  {
    name: "Earth (Normal)",
    shortLabel: "Earth",
    icon: "🌍",
    description: "Balanced classroom conditions",
    colors: {
      accent: "#2f80ed",
      accentSoft: "#cfe6ff",
      liquidA: "#4facfe",
      liquidB: "#62e6c6",
      glow: "#93d8ff",
      panel: "#eef8ff",
    },
  },
  {
    name: "Vacuum",
    shortLabel: "Vacuum",
    icon: "🌌",
    description: "No air, quiet transfer",
    colors: {
      accent: "#5d5fef",
      accentSoft: "#dfddff",
      liquidA: "#7a7ff5",
      liquidB: "#b59dff",
      glow: "#c8bcff",
      panel: "#f5f1ff",
    },
  },
  {
    name: "Pure Oxygen",
    shortLabel: "Oxygen",
    icon: "💨",
    description: "Lively and reactive",
    colors: {
      accent: "#0ea5e9",
      accentSoft: "#d7f2ff",
      liquidA: "#22c3ff",
      liquidB: "#7be3ff",
      glow: "#a5ecff",
      panel: "#eefcff",
    },
  },
  {
    name: "Inert Gas",
    shortLabel: "Inert",
    icon: "🫧",
    description: "Calm and stable",
    colors: {
      accent: "#64748b",
      accentSoft: "#e2e8f0",
      liquidA: "#94a3b8",
      liquidB: "#cbd5e1",
      glow: "#dbe4ef",
      panel: "#f7fafc",
    },
  },
  {
    name: "Acidic Environment",
    shortLabel: "Acidic",
    icon: "🔴",
    description: "Sharp low-pH energy",
    colors: {
      accent: "#ef476f",
      accentSoft: "#ffe0e7",
      liquidA: "#ff7b9c",
      liquidB: "#ffb36a",
      glow: "#ffc1d0",
      panel: "#fff4f7",
    },
  },
  {
    name: "Basic Environment",
    shortLabel: "Basic",
    icon: "🟢",
    description: "Smooth high-pH flow",
    colors: {
      accent: "#2fbf71",
      accentSoft: "#dff7ea",
      liquidA: "#42d392",
      liquidB: "#9ce15d",
      glow: "#c7f5ac",
      panel: "#f2fff7",
    },
  },
];

export const ENVIRONMENT_MAP = Object.fromEntries(
  ENVIRONMENTS.map((environment) => [environment.name, environment]),
);

export function getEnvironment(name) {
  return ENVIRONMENT_MAP[name] || ENVIRONMENTS[0];
}
