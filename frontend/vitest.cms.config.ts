import { defineConfig } from "vitest/config";
import path from "path";

/**
 * Dedicated Vitest configuration for CMS coverage reporting.
 *
 * This config keeps CMS coverage separate from the design-system gate
 * so that global thresholds are not affected by the current state of
 * the CMS module.
 */
export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: [
      "tests/**/*.test.ts",
      "tests/**/*.test.tsx",
      "src/design/**/*.test.tsx",
      "src/components/**/*.test.{ts,tsx}",
      "src/lib/**/*.test.{ts,tsx}",
      "src/app/**/*.test.{ts,tsx}",
    ],
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      reportsDirectory: "./coverage-cms",
      reporter: ["text", "html", "json-summary"],
      include: [
        "src/components/cms/**/*.{ts,tsx}",
        "src/app/plataforma/cms/**/*.{ts,tsx}",
        "src/lib/cms/**/*.{ts,tsx}",
      ],
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.stories.tsx",
        "src/app/plataforma/cms/**/*.stories.tsx",
      ],
      // No thresholds: this report is informational only.
      thresholds: {},
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
