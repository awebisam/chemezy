export function registerInventoryComposer(Alpine) {
  Alpine.data("inventoryComposer", () => ({
    get app() {
      return Alpine.store("app");
    },
  }));
}
