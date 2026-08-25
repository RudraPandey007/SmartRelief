/**
 * API client for the Relocation DSS backend.
 *
 * Reads VITE_API_BASE_URL and VITE_API_KEY from .env.local.
 * Throws structured errors on 401 / 429 / other non-2xx responses.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
const API_KEY = import.meta.env.VITE_API_KEY;

/**
 * @param {string} path  – e.g. "/villages" or "/relocation/generate-plan"
 * @param {RequestInit} [options] – extra fetch options (method, body, etc.)
 * @returns {Promise<any>} parsed JSON
 */
export async function apiFetch(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        ...(options.headers || {}),
      },
    });

    clearTimeout(timer);

    // Parse the body (works for both success and error shapes)
    let body;
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      body = await res.json();
    } else {
      body = await res.text();
    }

    if (res.ok) return body;

    // --- Structured error handling ---

    // 401: API key mismatch
    if (res.status === 401) {
      throw new ApiError(
        "AUTH_MISMATCH",
        "API key mismatch — check .env.local matches the backend .env APP_API_KEY value.",
        401,
        body
      );
    }

    // 429: Rate limit
    if (res.status === 429) {
      const retryAfter = res.headers.get("Retry-After") || "60";
      throw new ApiError(
        "RATE_LIMITED",
        `Rate limit reached. Try again in ${retryAfter} seconds.`,
        429,
        body
      );
    }

    // Other errors — surface the detail.message if available
    const message =
      (body && typeof body === "object" && body.detail && body.detail.message) ||
      (body && typeof body === "object" && body.detail) ||
      (typeof body === "string" ? body : `Request failed with status ${res.status}`);

    throw new ApiError("API_ERROR", String(message), res.status, body);
  } catch (err) {
    clearTimeout(timer);

    // Already an ApiError — re-throw
    if (err instanceof ApiError) throw err;

    // AbortController timeout
    if (err.name === "AbortError") {
      throw new ApiError(
        "TIMEOUT",
        "Request timed out after 8 seconds — is the backend running?",
        0,
        null
      );
    }

    // Network / CORS / DNS failures
    throw new ApiError(
      "NETWORK_ERROR",
      `Network error: ${err.message || "could not reach the backend"}.`,
      0,
      null
    );
  }
}

/**
 * Structured API error with a machine-readable `code`.
 */
export class ApiError extends Error {
  /**
   * @param {"AUTH_MISMATCH"|"RATE_LIMITED"|"API_ERROR"|"TIMEOUT"|"NETWORK_ERROR"} code
   * @param {string} message
   * @param {number} status
   * @param {*} body
   */
  constructor(code, message, status, body) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.body = body;
  }
}
