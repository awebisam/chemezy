import Alpine from "https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/+esm";
import { registerAppStore } from "./components/app-store.js";
import { registerAuthModal } from "./components/auth-modal.js";
import { registerDebugModal } from "./components/debug-modal.js";
import { registerInventoryComposer } from "./components/inventory-composer.js";
import { registerLabStage } from "./components/lab-stage.js";
import { registerLandingHero } from "./components/landing.js";
import { registerNotificationsPanel } from "./components/notifications.js";
import { registerPlayerSidebar } from "./components/player-sidebar.js";

window.Alpine = Alpine;

registerAppStore(Alpine);
registerLandingHero(Alpine);
registerLabStage(Alpine);
registerInventoryComposer(Alpine);
registerPlayerSidebar(Alpine);
registerAuthModal(Alpine);
registerDebugModal(Alpine);
registerNotificationsPanel(Alpine);

Alpine.data("appShell", () => ({
  get app() {
    return Alpine.store("app");
  },

  init() {
    this.app.init();
  },
}));

Alpine.start();
