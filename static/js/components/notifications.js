export function registerNotificationsPanel(Alpine) {
  Alpine.data("notificationsPanel", () => ({
    get app() {
      return Alpine.store("app");
    },
  }));
}
