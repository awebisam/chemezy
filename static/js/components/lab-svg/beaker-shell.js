export const BEAKER_VIEWBOX = "0 0 360 420";
export const VESSEL_PATH = "M92 36V260C92 305 126 338 164 344H196C234 338 268 305 268 260V36";
export const CLIP_PATH = `${VESSEL_PATH}Z`;

export function buildBeakerBackdrop({
  glowId,
  panelFill = "#ffffff",
  shadowFill = "#c7dbff",
} = {}) {
  return `
    <rect x="34" y="18" width="292" height="376" rx="38" fill="${panelFill}" opacity="0.55" />
    <ellipse cx="180" cy="344" rx="112" ry="20" fill="${shadowFill}" opacity="0.22" />
    <circle cx="182" cy="214" r="126" fill="url(#${glowId})" class="scene-glow" />
  `;
}

export function buildBeakerGlassCore({
  bodyFill = "#ffffff",
  strokeColor = "#3f69c6",
  rimFill = "#eff7ff",
  rimHighlight = "#d7ebff",
} = {}) {
  return `
    <path d="${VESSEL_PATH}" fill="${bodyFill}" opacity="0.7" />
    <path d="${VESSEL_PATH}" fill="none" stroke="${strokeColor}" stroke-width="5" stroke-linejoin="round" />
    <path d="${VESSEL_PATH}" fill="none" stroke="${rimHighlight}" stroke-width="2.5" stroke-linejoin="round" opacity="0.9" />
    <rect x="82" y="24" width="196" height="22" rx="11" fill="${rimFill}" stroke="${strokeColor}" stroke-width="4" />
    <path d="M115 66v248" stroke="#ffffff" stroke-opacity="0.5" stroke-width="8" stroke-linecap="round" />
    <path d="M246 80v202" stroke="#ffffff" stroke-opacity="0.16" stroke-width="4" stroke-linecap="round" />
  `;
}

export function buildBeakerForeground({ shineColor = "#ffffff" } = {}) {
  return `
    <path d="M92 78 Q182 54 268 84" fill="none" stroke="${shineColor}" stroke-opacity="0.46" stroke-width="10" stroke-linecap="round" />
    <path d="M98 140v104" fill="none" stroke="${shineColor}" stroke-opacity="0.34" stroke-width="6" stroke-linecap="round" />
  `;
}

export function buildBeakerHud({
  environmentIcon,
  environmentName,
  effectCount,
  formulas,
} = {}) {
  return `
    <rect x="74" y="20" width="212" height="36" rx="18" fill="#ffffff" opacity="0.8" />
    <text x="92" y="42" class="scene-hud-label">${environmentIcon} ${environmentName}</text>
    <text x="272" y="42" class="scene-hud-meta" text-anchor="end">${effectCount} effect${effectCount === 1 ? "" : "s"}</text>
    <rect x="82" y="360" width="196" height="36" rx="18" fill="#ffffff" opacity="0.82" />
    <text x="180" y="383" class="scene-hud-meta" text-anchor="middle">${formulas}</text>
  `;
}
