import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/**/*.test.ts", "src/design/**/*.test.tsx"],
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      // Coverage scoped to the design system — the only module with tests.
      // Expand the include glob and raise thresholds as more tests are added.
      thresholds: {
        lines: 40,
        branches: 30,
        functions: 40,
        statements: 40,
      },
      include: ["src/design/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.stories.tsx",
        "src/design/**/*.stories.tsx",
        "src/design/index.ts",
      ],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
