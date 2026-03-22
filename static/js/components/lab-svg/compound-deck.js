import { clamp, escapeHtml, safeColor } from "../../utils/formatters.js";

export function buildCompoundDeckBackdrop({
  itemCount = 0,
  activeCount = 0,
  accentColor = "#4f7cff",
  label = "Compound deck",
} = {}) {
  const safeAccent = safeColor(accentColor, "#4f7cff");
  const slots = Math.max(6, Math.min(12, itemCount || 6));
  const slotWidth = 104;
  const laneWidth = slots * slotWidth;
  const laneX = 600 - laneWidth / 2;
  const fillOpacity = clamp(0.18 + activeCount * 0.06, 0.18, 0.5);

  return `
    <svg class="deck-svg" viewBox="0 0 1200 220" role="img" aria-label="${escapeHtml(label)}">
      <defs>
        <linearGradient id="deckRailGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#ffffff" stop-opacity="0.98" />
          <stop offset="100%" stop-color="${safeAccent}" stop-opacity="0.18" />
        </linearGradient>
      </defs>
      <rect x="42" y="42" width="1116" height="136" rx="42" fill="url(#deckRailGradient)" />
      <rect x="70" y="72" width="1060" height="76" rx="28" fill="#f9fcff" opacity="0.92" />
      <rect x="92" y="146" width="1016" height="20" rx="10" fill="${safeAccent}" opacity="${fillOpacity}" />
      ${Array.from({ length: slots }, (_, index) => {
        const x = laneX + index * slotWidth;
        return `
          <rect x="${x}" y="86" width="74" height="54" rx="22" fill="#ffffff" opacity="0.76" />
          <rect x="${x + 22}" y="104" width="30" height="12" rx="6" fill="${safeAccent}" opacity="0.18" />
        `;
      }).join("")}
      <circle cx="124" cy="110" r="22" fill="${safeAccent}" opacity="0.12" />
      <circle cx="1074" cy="110" r="28" fill="${safeAccent}" opacity="0.08" />
      <text x="112" y="116" class="deck-svg__label">${escapeHtml(label)}</text>
      <text x="1088" y="116" class="deck-svg__meta" text-anchor="end">${itemCount} ready</text>
    </svg>
  `;
}
