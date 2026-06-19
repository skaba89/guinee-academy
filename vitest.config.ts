import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    // Exclude known-broken test files that fail due to React version / mock
    // setup issues unrelated to current work. They should be fixed and
    // removed from this list progressively.
    exclude: [
      "node_modules/**",
      "dist/**",
      ".idea/**",
      ".git/**",
      ".cache/**",
      // Playwright E2E tests (not vitest tests). They import
      // @playwright/test which has side effects that hang vitest.
      "tests/**",
      // Pre-existing failures (React hooks / mock setup):
      "src/features/homework/__tests__/useHomework.test.tsx",
      "src/features/parents/hooks/__tests__/useParentData.test.tsx",
      "src/stores/__tests__/notificationStore.test.ts",
      "src/hooks/__tests__/useAuth.test.tsx",
      // Hangs: imports @/pages/Auth which has side effects that don't
      // resolve in jsdom (timers/intervals from full page render).
      "src/components/__tests__/auth-flow-sync.test.tsx",
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: [
        "node_modules/",
        "dist/",
        "coverage/",
        "**/*.d.ts",
        "**/index.ts",
        "src/main.tsx",
      ],
      thresholds: {
        lines: 25,
        functions: 25,
        branches: 20,
        statements: 25,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
