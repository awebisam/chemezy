import { escapeHtml } from "../utils/formatters.js";
import { getEffectDisplay, normalizeEffects } from "../utils/effects.js";

export function buildEffectInspector(effects = []) {
  const normalized = normalizeEffects(effects);
  if (!normalized.length) {
    return `
      <div class="empty-state empty-state--compact">
        <strong>No active effect layers yet.</strong>
        <span>Mix compounds to populate this inspector with live visuals and values.</span>
      </div>
    `;
  }

  return normalized
    .map((effect) => {
      const display = getEffectDisplay(effect);
      const facts = display.facts
        .map(
          (fact) => `
            <div class="effect-fact">
              <span>${escapeHtml(fact.label)}</span>
              <strong>${escapeHtml(fact.value)}</strong>
            </div>
          `,
        )
        .join("");

      return `
        <article class="effect-card effect-card--${display.tone}">
          <div class="effect-card__heading">
            <h4>${escapeHtml(display.title)}</h4>
            <span class="effect-chip">${escapeHtml(effect.effect_type)}</span>
          </div>
          <p>${escapeHtml(display.description)}</p>
          <div class="effect-facts">${facts}</div>
        </article>
      `;
    })
    .join("");
}
