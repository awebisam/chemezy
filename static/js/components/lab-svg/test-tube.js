import { clamp, escapeHtml, safeColor, titleCase } from "../../utils/formatters.js";

export function buildTestTubeSvg({
  chemical = {},
  source = "inventory",
  active = false,
  size = "deck",
  tubeId = "tube",
} = {}) {
  const safeColorValue = safeColor(chemical.color, "#8bb6ff");
  const quantity = clamp(Number(chemical.quantity || 1), 0.25, 5);
  const liquidHeight = clamp(54 + quantity * 18, 62, 126);
  const liquidY = 190 - liquidHeight;
  const state = titleCase(chemical.state_of_matter || "Unknown");
  const sourceLabel = source === "bench" ? "Bench" : "Inventory";
  const shellTone = source === "bench" ? "#ffbf47" : "#4f7cff";
  const surfaceOpacity = active ? 0.94 : 0.72;
  const tubeClasses = [
    "tube-svg",
    `tube-svg--${size}`,
    active ? "tube-svg--queued" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const gradientId = `${tubeId}-liquid`;
  const labelId = `${tubeId}-label`;

  return `
    <svg class="${tubeClasses}" viewBox="0 0 120 240" role="img" aria-labelledby="${labelId}">
      <defs>
        <linearGradient id="${gradientId}" x1="0%" y1="100%" x2="0%" y2="0%">
          <stop offset="0%" stop-color="${safeColorValue}" stop-opacity="0.94" />
          <stop offset="100%" stop-color="#ffffff" stop-opacity="0.86" />
        </linearGradient>
      </defs>
      <title id="${labelId}">${escapeHtml(chemical.molecular_formula || "Compound")} test tube</title>
      <ellipse cx="60" cy="212" rx="36" ry="11" fill="${shellTone}" opacity="0.14" />
      <rect x="28" y="24" width="64" height="26" rx="13" fill="#eff7ff" stroke="${shellTone}" stroke-width="4" />
      <path d="M34 42V182C34 204 46 216 60 220C74 216 86 204 86 182V42" fill="#ffffff" opacity="0.88" />
      <path d="M34 42V182C34 204 46 216 60 220C74 216 86 204 86 182V42" fill="none" stroke="${shellTone}" stroke-width="4" stroke-linejoin="round" />
      <rect x="38" y="${liquidY}" width="44" height="${liquidHeight}" rx="20" fill="url(#${gradientId})" opacity="${surfaceOpacity}" />
      <path d="M38 ${liquidY + 12} C46 ${liquidY + 2}, 58 ${liquidY + 10}, 82 ${liquidY + 8} V190 H38 Z" fill="#ffffff" opacity="0.42" />
      <path d="M46 68v112" stroke="#ffffff" stroke-opacity="0.52" stroke-width="6" stroke-linecap="round" />
      <circle cx="52" cy="${liquidY + 28}" r="4" fill="#ffffff" opacity="0.4" />
      <circle cx="68" cy="${liquidY + 52}" r="3" fill="#ffffff" opacity="0.34" />
      <rect x="14" y="8" width="46" height="20" rx="10" fill="${shellTone}" opacity="0.14" />
      <text x="37" y="22" class="tube-svg__meta" text-anchor="middle">${sourceLabel}</text>
      <text x="60" y="110" class="tube-svg__formula" text-anchor="middle">${escapeHtml(chemical.molecular_formula || "Mix")}</text>
      <text x="60" y="132" class="tube-svg__state" text-anchor="middle">${escapeHtml(state)}</text>
    </svg>
  `;
}
