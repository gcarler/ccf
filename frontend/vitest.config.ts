import { defineConfig } from "vitest/config";
import path from "path";

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
      "src/hooks/**/*.test.{ts,tsx}",
      "src/lib/**/*.test.{ts,tsx}",
      "src/app/**/*.test.{ts,tsx}",
    ],
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      // Coverage gate scoped to the design system. The full component suite
      // still runs above, while each product area can adopt its own coverage
      // scope as its tests become part of the quality contract.
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
