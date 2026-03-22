export function registerAuthModal(Alpine) {
  Alpine.data("authModal", () => ({
    get app() {
      return Alpine.store("app");
    },
  }));
}
