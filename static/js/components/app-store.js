import { createApiClient } from "../api.js";
import { ENVIRONMENTS, getEnvironment } from "../config/environments.js";
import { PREVIEW_REACTION } from "../utils/effects.js";
import { formatDateTime, uniqBy } from "../utils/formatters.js";

export function registerAppStore(Alpine) {
  const store = createStore();
  store.api = createApiClient({
    getToken: () => store.authToken,
    onUnauthorized: () => store.logout(true),
  });
  Alpine.store("app", store);
}

function createStore() {
  return {
    api: null,
    initialized: false,
    loading: true,
    loadingProgress: 0,
    viewportWidth: 1400,
    isAuthenticated: false,
    authToken: null,
    username: "",
    currentUser: null,

    showLoginModal: false,
    showTutorial: false,
    showDebugModal: false,
    showPlaygroundModal: false,
    showWorldFirstEffect: false,
    activeMobileTab: "lab",

    notifications: [],
    toastCounter: 0,

    loginForm: {
      username: "",
      password: "",
      loading: false,
    },

    newChemical: "",
    chemicalContext: "",
    chemicalSearch: "",
    isAddingChemical: false,
    debugApiUrl: "/chemicals/",
    debugApiResult: "",
    changeRequestId: "",
    changeRequestReason: "",

    isDragging: false,
    isReacting: false,
    environments: ENVIRONMENTS,
    selectedEnvironment: ENVIRONMENTS[0].name,
    selectedCatalyst: "",
    chemicals: [],
    reactants: [],
    benchProducts: [],
    lastReaction: null,
    myAwards: [],
    leaderboard: [],
    selectedLeaderboardCategory: "discovery",
    reactionStats: {
      total_reactions: 0,
      total_discoveries: 0,
    },
    dashboardStats: null,
    awardNotifications: [],
    previewReaction: PREVIEW_REACTION,

    get isAdmin() {
      return Boolean(this.currentUser?.is_admin);
    },

    get isMobileLayout() {
      return this.viewportWidth < 1080;
    },

    get currentEnvironment() {
      return getEnvironment(this.selectedEnvironment);
    },

    get filteredChemicals() {
      const search = this.chemicalSearch.trim().toLowerCase();
      return this.chemicals.filter((chemical) =>
        matchesChemicalSearch(chemical, search),
      );
    },

    get playgroundDeck() {
      const search = this.chemicalSearch.trim().toLowerCase();
      const reactantIds = new Set(this.reactants.map((reactant) => reactant.id));
      const benchEntries = this.benchProducts
        .map((product) => ({
          ...enrichChemicalRecord(product, this.chemicals),
          deck_source: "bench",
        }))
        .filter((chemical) => matchesChemicalSearch(chemical, search));
      const inventoryEntries = this.chemicals
        .map((chemical) => ({
          ...chemical,
          deck_source: "inventory",
        }))
        .filter((chemical) => matchesChemicalSearch(chemical, search));

      return uniqBy(
        [...benchEntries, ...inventoryEntries],
        (chemical) => chemical.id ?? chemical.chemical_id ?? chemical.molecular_formula,
      ).sort((left, right) => {
        const leftId = left.id ?? left.chemical_id;
        const rightId = right.id ?? right.chemical_id;
        const leftActive = Number(reactantIds.has(leftId));
        const rightActive = Number(reactantIds.has(rightId));

        if (leftActive !== rightActive) {
          return rightActive - leftActive;
        }

        if (left.deck_source !== right.deck_source) {
          return left.deck_source === "bench" ? -1 : 1;
        }

        return String(left.molecular_formula || "").localeCompare(
          String(right.molecular_formula || ""),
        );
      });
    },

    get featuredAwards() {
      return this.myAwards.slice(0, 4);
    },

    get achievementProgress() {
      return this.dashboardStats?.progress?.progress_percentage || 0;
    },

    syncViewport() {
      this.viewportWidth = window.innerWidth;
      if (!this.isMobileLayout) {
        this.activeMobileTab = "lab";
      }
    },

    async init() {
      if (this.initialized) {
        return;
      }

      this.initialized = true;
      this.syncViewport();
      window.addEventListener("resize", () => this.syncViewport());

      for (let step = 0; step <= 100; step += 20) {
        this.loadingProgress = step;
        await delay(70);
      }

      const storedToken = localStorage.getItem("chemezy_token");
      const storedUsername = localStorage.getItem("chemezy_username");

      if (storedToken && storedUsername) {
        this.authToken = storedToken;
        this.username = storedUsername;
        this.isAuthenticated = true;
        await this.loadInitialData();
      }

      this.loading = false;
    },

    async loadInitialData() {
      const currentUser = await this.fetchCurrentUser();
      if (!currentUser) {
        return;
      }

      const results = await Promise.allSettled([
        this.fetchChemicals(),
        this.fetchAwards(),
        this.fetchLeaderboard(),
        this.fetchReactionStats(),
        this.fetchDashboardStats(),
        this.fetchNotifications(),
      ]);

      if (results[0].status === "rejected") {
        this.pushToast(
          "Lab inventory unavailable",
          "error",
          "The frontend loaded, but chemicals could not be fetched.",
        );
      }
    },

    async fetchCurrentUser() {
      if (!this.authToken) {
        return null;
      }

      try {
        this.currentUser = await this.api.request("/auth/me");
        return this.currentUser;
      } catch (error) {
        this.currentUser = null;
        return null;
      }
    },

    async fetchChemicals() {
      const payload = await this.api.request("/chemicals/");
      this.chemicals = payload?.results || [];
      this.benchProducts = this.benchProducts.map((product) =>
        enrichChemicalRecord(product, this.chemicals),
      );
      return this.chemicals;
    },

    async fetchAwards() {
      try {
        this.myAwards = (await this.api.request("/awards/me")) || [];
      } catch (error) {
        this.myAwards = [];
      }

      return this.myAwards;
    },

    async fetchLeaderboard() {
      try {
        this.leaderboard =
          (await this.api.request(
            `/awards/leaderboard/${this.selectedLeaderboardCategory}`,
          )) || [];
      } catch (error) {
        this.leaderboard = [];
      }

      return this.leaderboard;
    },

    async fetchReactionStats() {
      try {
        this.reactionStats =
          (await this.api.request("/reactions/stats")) || this.reactionStats;
      } catch (error) {
        this.reactionStats = {
          total_reactions: 0,
          total_discoveries: 0,
        };
      }

      return this.reactionStats;
    },

    async fetchDashboardStats() {
      try {
        const payload = await this.api.request("/awards/dashboard/stats");
        this.dashboardStats = payload?.dashboard_stats || null;
      } catch (error) {
        this.dashboardStats = null;
      }

      return this.dashboardStats;
    },

    async fetchNotifications() {
      try {
        const payload = await this.api.request("/awards/notifications");
        this.awardNotifications = (payload?.notifications || []).map((item) => ({
          ...item,
          title: sanitizeNotificationText(item.title),
          message: sanitizeNotificationText(item.message),
          timestamp: formatDateTime(item.timestamp),
        }));
      } catch (error) {
        this.awardNotifications = [];
      }

      return this.awardNotifications;
    },

    openLogin() {
      this.showLoginModal = true;
    },

    closeLogin() {
      this.showLoginModal = false;
    },

    openPlayground() {
      this.activeMobileTab = "lab";
      this.showPlaygroundModal = true;
    },

    closePlayground() {
      this.showPlaygroundModal = false;
      this.isDragging = false;
    },

    async handleLogin() {
      this.loginForm.loading = true;
      try {
        const formData = new URLSearchParams();
        formData.append("username", this.loginForm.username);
        formData.append("password", this.loginForm.password);

        const payload = await this.api.request("/auth/token", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: formData,
        });

        this.authToken = payload.access_token;
        this.username = this.loginForm.username;
        this.isAuthenticated = true;
        localStorage.setItem("chemezy_token", this.authToken);
        localStorage.setItem("chemezy_username", this.username);
        this.loginForm.password = "";
        this.showLoginModal = false;
        await this.loadInitialData();
        this.openPlayground();
        this.pushToast("Lab access granted", "success", `Welcome back, ${this.username}.`);
      } catch (error) {
        this.pushToast("Login failed", "error", error.message);
      } finally {
        this.loginForm.loading = false;
      }
    },

    logout(sessionExpired = false) {
      this.isAuthenticated = false;
      this.authToken = null;
      this.username = "";
      this.currentUser = null;
      this.showPlaygroundModal = false;
      this.chemicals = [];
      this.reactants = [];
      this.benchProducts = [];
      this.lastReaction = null;
      this.myAwards = [];
      this.leaderboard = [];
      this.dashboardStats = null;
      this.awardNotifications = [];
      this.selectedCatalyst = "";
      localStorage.removeItem("chemezy_token");
      localStorage.removeItem("chemezy_username");

      if (sessionExpired) {
        this.pushToast("Session expired", "error", "Please log in again.");
      } else {
        this.pushToast("Logged out", "info", "Your lab session has been closed.");
      }
    },

    async addChemical() {
      if (!this.newChemical.trim()) {
        return;
      }

      this.isAddingChemical = true;
      try {
        const payload = await this.api.request("/chemicals/", {
          method: "POST",
          body: JSON.stringify({
            molecular_formula: this.newChemical.trim(),
            context: this.chemicalContext.trim() || null,
          }),
        });

        this.chemicals = uniqBy(
          [payload, ...this.chemicals].map((chemical) =>
            enrichChemicalRecord(chemical, this.chemicals),
          ),
          (chemical) => chemical.id,
        );

        this.newChemical = "";
        this.chemicalContext = "";
        this.pushToast(
          "Compound added",
          "success",
          `${payload.molecular_formula} is now in your lab cart.`,
        );
      } catch (error) {
        this.pushToast("Compound add failed", "error", error.message);
      } finally {
        this.isAddingChemical = false;
      }
    },

    setMobileTab(tab) {
      this.activeMobileTab = tab;
    },

    loadReactant(chemical) {
      const record = enrichChemicalRecord(chemical, this.chemicals);
      const chemicalId = record.id ?? record.chemical_id;
      if (!chemicalId) {
        return;
      }

      if (this.reactants.some((reactant) => reactant.id === chemicalId)) {
        this.pushToast("Already queued", "warning", "That compound is already in the mixer.");
        return;
      }

      this.reactants.push({
        ...record,
        id: chemicalId,
        chemical_id: chemicalId,
      });
      this.pushToast(
        "Compound loaded",
        "info",
        `${record.molecular_formula} moved into the reaction chamber.`,
      );
    },

    removeReactant(index) {
      this.reactants.splice(index, 1);
    },

    startDrag(event, chemical) {
      const payload = enrichChemicalRecord(chemical, this.chemicals);
      const id = payload.id ?? payload.chemical_id;
      if (!event.dataTransfer || !id) {
        return;
      }

      event.dataTransfer.effectAllowed = "copy";
      event.dataTransfer.setData(
        "chemical",
        JSON.stringify({
          ...payload,
          id,
          chemical_id: id,
        }),
      );
      this.isDragging = true;
      event.currentTarget?.classList.add("is-dragging");
    },

    endDrag(event) {
      this.isDragging = false;
      event.currentTarget?.classList.remove("is-dragging");
    },

    handleDrop(event) {
      event.preventDefault();
      this.isDragging = false;

      try {
        const payload = JSON.parse(event.dataTransfer.getData("chemical"));
        this.loadReactant(payload);
      } catch (error) {
        this.pushToast("Drop failed", "error", "That item could not be loaded.");
      }
    },

    async runReaction() {
      if (!this.reactants.length || this.isReacting) {
        return;
      }

      this.isReacting = true;
      try {
        const response = await this.api.request("/reactions/react", {
          method: "POST",
          body: JSON.stringify({
            reactants: this.reactants.map((reactant) => ({
              chemical_id: reactant.id,
              quantity: 1.0,
            })),
            catalyst_id: this.selectedCatalyst ? Number(this.selectedCatalyst) : null,
            environment: this.selectedEnvironment,
          }),
        });

        this.lastReaction = {
          ...response,
          reactants: this.reactants.map((reactant) => ({
            molecular_formula: reactant.molecular_formula,
            common_name: reactant.common_name,
            quantity: 1,
          })),
          environment: this.selectedEnvironment,
          environmentConfig: this.currentEnvironment,
        };

        this.addProductsToBench(response.products || []);
        this.reactants = [];
        this.selectedCatalyst = "";

        await Promise.allSettled([
          this.fetchChemicals(),
          this.fetchAwards(),
          this.fetchReactionStats(),
          this.fetchDashboardStats(),
          this.fetchNotifications(),
        ]);

        if (response.is_world_first) {
          this.triggerWorldFirst();
        }

        this.pushToast("Reaction complete", "success", "The new effect stack is ready to inspect.");
      } catch (error) {
        this.pushToast("Reaction failed", "error", error.message);
      } finally {
        this.isReacting = false;
      }
    },

    addProductsToBench(products) {
      products.forEach((product) => {
        const hydrated = enrichChemicalRecord(
          {
            ...product,
            id: product.chemical_id,
          },
          this.chemicals,
        );
        const existing = this.benchProducts.find(
          (item) => item.chemical_id === hydrated.chemical_id,
        );

        if (existing) {
          existing.quantity += hydrated.quantity;
        } else {
          this.benchProducts.push(hydrated);
        }
      });
    },

    removeFromBench(chemicalId) {
      this.benchProducts = this.benchProducts.filter(
        (product) => product.chemical_id !== chemicalId,
      );
    },

    triggerWorldFirst() {
      this.showWorldFirstEffect = true;
      this.pushToast("World first!", "warning", "You created a brand new discovery.");
      window.setTimeout(() => {
        this.showWorldFirstEffect = false;
      }, 2400);
    },

    resolveChemical(chemicalId) {
      return this.chemicals.find((chemical) => chemical.id === chemicalId) || null;
    },

    productDetails(product) {
      return enrichChemicalRecord(product, this.chemicals);
    },

    async markNotificationsRead() {
      if (!this.awardNotifications.length) {
        return;
      }

      try {
        await this.api.request("/awards/notifications/read", {
          method: "POST",
          body: JSON.stringify({
            notification_ids: this.awardNotifications.map(
              (notification) => notification.id,
            ),
          }),
        });
        await this.fetchNotifications();
        this.pushToast("Notifications cleared", "info", "Your award alerts were marked as read.");
      } catch (error) {
        this.pushToast("Notification update failed", "error", error.message);
      }
    },

    async clearChemicals() {
      if (!this.isAdmin) {
        this.pushToast("Admin only", "error", "You need admin access for this action.");
        return;
      }

      if (!window.confirm("Clear all chemicals?")) {
        return;
      }

      try {
        await this.api.request("/debug/chemicals/clear", { method: "DELETE" });
        this.chemicals = [];
        this.reactants = [];
        this.benchProducts = [];
        this.pushToast("Chemicals cleared", "success", "The inventory was reset.");
      } catch (error) {
        this.pushToast("Debug action failed", "error", error.message);
      }
    },

    async clearReactions() {
      if (!this.isAdmin) {
        this.pushToast("Admin only", "error", "You need admin access for this action.");
        return;
      }

      if (!window.confirm("Clear all reactions?")) {
        return;
      }

      try {
        await this.api.request("/debug/reactions/clear", { method: "DELETE" });
        this.lastReaction = null;
        this.pushToast("Reactions cleared", "success", "Reaction history was reset.");
      } catch (error) {
        this.pushToast("Debug action failed", "error", error.message);
      }
    },

    async refreshData() {
      if (!this.isAdmin) {
        this.pushToast("Admin only", "error", "You need admin access for this action.");
        return;
      }

      await this.loadInitialData();
      this.pushToast("Data refreshed", "success", "Dashboard panels were reloaded.");
    },

    async testApi() {
      if (!this.isAdmin) {
        this.pushToast("Admin only", "error", "You need admin access for this action.");
        return;
      }

      if (!this.debugApiUrl.trim()) {
        this.pushToast("Missing endpoint", "warning", "Enter an API path to test.");
        return;
      }

      try {
        const payload = await this.api.request(this.debugApiUrl.trim());
        this.debugApiResult = JSON.stringify(payload, null, 2);
      } catch (error) {
        this.debugApiResult = JSON.stringify(
          {
            status: error.status || 500,
            detail: error.message,
          },
          null,
          2,
        );
      }
    },

    async submitChangeRequest() {
      if (!this.isAdmin) {
        this.pushToast("Admin only", "error", "You need admin access for this action.");
        return;
      }

      if (!this.changeRequestId || !this.changeRequestReason.trim()) {
        this.pushToast("Missing fields", "warning", "Pick a chemical and explain the request.");
        return;
      }

      try {
        await this.api.request(`/debug/chemicals/${this.changeRequestId}`, {
          method: "DELETE",
          body: JSON.stringify({
            reason: this.changeRequestReason.trim(),
          }),
        });
        this.changeRequestId = "";
        this.changeRequestReason = "";
        this.pushToast("Change request sent", "success", "The debug deletion request was submitted.");
      } catch (error) {
        this.pushToast("Change request failed", "error", error.message);
      }
    },

    pushToast(title, type = "info", message = "") {
      const toast = {
        id: `${Date.now()}-${this.toastCounter++}`,
        title,
        type,
        message,
      };
      this.notifications.push(toast);

      window.setTimeout(() => {
        this.dismissToast(toast.id);
      }, 4200);
    },

    dismissToast(id) {
      this.notifications = this.notifications.filter((toast) => toast.id !== id);
    },
  };
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function sanitizeNotificationText(value) {
  return String(value || "").replace(/[<>�]/g, "").trim();
}

function matchesChemicalSearch(chemical, search) {
  if (!search) {
    return true;
  }

  const formula = chemical.molecular_formula?.toLowerCase() || "";
  const commonName = chemical.common_name?.toLowerCase() || "";
  const state = chemical.state_of_matter?.toLowerCase() || "";

  return (
    formula.includes(search) ||
    commonName.includes(search) ||
    state.includes(search)
  );
}

function enrichChemicalRecord(record, catalog) {
  const id = record.id ?? record.chemical_id ?? null;
  const source =
    catalog.find((chemical) => chemical.id === id) ||
    record;

  return {
    ...source,
    ...record,
    id,
    chemical_id: record.chemical_id ?? id,
    quantity: Number(record.quantity || 1),
    molecular_formula:
      record.molecular_formula || source.molecular_formula || "Unknown",
    common_name: record.common_name || source.common_name || "Uncatalogued Compound",
    color: record.color || source.color || "#8bb6ff",
    state_of_matter:
      record.state_of_matter || source.state_of_matter || "unknown",
  };
}
