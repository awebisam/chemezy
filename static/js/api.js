export function createApiClient({
  baseUrl = "/api/v1",
  getToken,
  onUnauthorized,
} = {}) {
  return {
    async request(endpoint, options = {}) {
      const headers = new Headers(options.headers || {});
      const token = typeof getToken === "function" ? getToken() : null;
      const body = options.body;
      const isFormBody =
        typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams;

      if (!headers.has("Content-Type") && body && !isFormBody) {
        headers.set("Content-Type", "application/json");
      }

      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }

      const response = await fetch(`${baseUrl}${endpoint}`, {
        ...options,
        headers,
      });

      const isJson =
        response.headers.get("content-type")?.includes("application/json") ?? false;
      const payload =
        response.status === 204
          ? null
          : isJson
            ? await response.json()
            : await response.text();

      if (!response.ok) {
        const detail =
          typeof payload === "string"
            ? payload
            : payload?.detail || `HTTP ${response.status}`;

        if (response.status === 401 && typeof onUnauthorized === "function") {
          onUnauthorized();
        }

        const error = new Error(detail);
        error.status = response.status;
        error.payload = payload;
        throw error;
      }

      return payload;
    },
  };
}
