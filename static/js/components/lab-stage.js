import { buildBeakerScene } from "./beaker-scene.js";
import { buildEffectInspector } from "./effect-inspector.js";
import { buildCompoundDeckBackdrop } from "./lab-svg/compound-deck.js";
import { buildTestTubeSvg } from "./lab-svg/test-tube.js";

export function registerLabStage(Alpine) {
  Alpine.data("labStage", () => ({
    get app() {
      return Alpine.store("app");
    },

    get sceneMarkup() {
      return this.buildSceneMarkup("modal");
    },

    get launcherSceneMarkup() {
      return this.buildSceneMarkup("launcher");
    },

    get inspectorMarkup() {
      return buildEffectInspector(this.app.lastReaction?.effects || []);
    },

    get deckBackdropMarkup() {
      return buildCompoundDeckBackdrop({
        itemCount: this.app.playgroundDeck.length,
        activeCount: this.app.reactants.length,
        accentColor: this.app.currentEnvironment.colors.accent,
        label: `${this.app.currentEnvironment.shortLabel} compound deck`,
      });
    },

    buildSceneMarkup(size = "modal") {
      const sceneReactants = this.app.reactants.length
        ? this.app.reactants
        : this.app.lastReaction?.reactants || [];
      const sceneId = `${size}-${this.app.selectedEnvironment
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")}`;

      return buildBeakerScene({
        environment: this.app.selectedEnvironment,
        reactants: sceneReactants,
        products: this.app.lastReaction?.products || [],
        effects: this.app.lastReaction?.effects || [],
        isReacting: this.app.isReacting,
        size,
        sceneId,
      });
    },

    tubeMarkup(chemical, index) {
      const chemicalId = chemical.id ?? chemical.chemical_id ?? index;
      return buildTestTubeSvg({
        chemical,
        source: chemical.deck_source,
        active: this.isQueued(chemical),
        size: "deck",
        tubeId: `deck-${chemicalId}-${index}`,
      });
    },

    isQueued(chemical) {
      const chemicalId = chemical.id ?? chemical.chemical_id;
      return this.app.reactants.some((reactant) => reactant.id === chemicalId);
    },

    handleDrop(event) {
      this.app.handleDrop(event);
    },
  }));
}
