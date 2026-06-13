/**
 * Guinée Academy — Runtime Configuration
 * ========================================
 * This file is loaded at runtime (NOT bundled by Vite).
 * Edit this file in the `dist/` folder AFTER building to configure
 * the API endpoint for your deployment environment.
 *
 * DO NOT edit the source file — it gets copied to dist/ at build time.
 * Instead, edit dist/config.js on your server or hosting platform.
 *
 * Examples:
 *   Render:     https://guinee-academy-api-xxxx.onrender.com
 *   Railway:    https://guinee-academy-api.up.railway.app
 *   Local:      http://localhost:8000
 */
window.__GUINEE_ACADEMY_CONFIG__ = {
  /**
   * Backend API base URL.
   * - Set to your backend URL (e.g. "https://guinee-academy-api-xxxx.onrender.com")
   *   to bypass the /api-proxy and call the API directly.
   * - Set to "" (empty) to use the /api-proxy path (requires nginx proxy).
   */
  API_URL: "",  // Set your backend API URL here after deployment (e.g. "https://guinee-academy-api-xxxx.onrender.com")
};
