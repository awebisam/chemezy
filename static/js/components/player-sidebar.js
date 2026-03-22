export function registerPlayerSidebar(Alpine) {
  Alpine.data("playerSidebar", () => ({
    get app() {
      return Alpine.store("app");
    },
  }));
}
