import { ENVIRONMENTS } from "../config/environments.js";
import { buildBeakerScene } from "./beaker-scene.js";

export function registerLandingHero(Alpine) {
  Alpine.data("landingHero", () => ({
    previewEnvironment: ENVIRONMENTS[2],
    featuredCards: [
      {
        title: "Layered SVG Effects",
        body: "Gas, glow, foam, texture, heat, and spills all stack inside one beaker.",
      },
      {
        title: "Real API Payloads",
        body: "The renderer is shaped around the existing reaction effect schema, not fake frontend-only data.",
      },
      {
        title: "Playful Lab Flow",
        body: "Inventory, mixing, rewards, and ranking now feel like a simple game instead of one giant page.",
      },
    ],

    get app() {
      return Alpine.store("app");
    },

    get environments() {
      return ENVIRONMENTS;
    },

    get previewSceneMarkup() {
      return buildBeakerScene({
        environment: this.app.previewReaction.environment,
        reactants: this.app.previewReaction.reactants,
        products: this.app.previewReaction.products,
        effects: this.app.previewReaction.effects,
        size: "hero",
        sceneId: "landing-preview",
      });
    },
  }));
}
