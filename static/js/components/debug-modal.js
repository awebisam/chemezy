export function registerDebugModal(Alpine) {
  Alpine.data("debugModal", () => ({
    get app() {
      return Alpine.store("app");
    },
  }));
}
