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
      reporter: ["text", "html", "lcov", "json-summary"],
      // Coverage scoped to the design system — the only module with tests.
      // Expand the include glob and raise thresholds as more tests are added.
      thresholds: {
        lines: 40,
        branches: 30,
        functions: 40,
        statements: 40,
      },
      include: [
        "src/design/**/*.{ts,tsx}",
        "src/components/**/*.{ts,tsx}",
        "src/app/plataforma/messages/_hooks/useUserSearch.ts",
        "src/app/plataforma/messages/_hooks/useChatThread.ts",
        "src/app/plataforma/messages/_components/MessageInput.tsx",
        "src/app/plataforma/messages/page.tsx",
        "src/app/plataforma/inbox/chat/page.tsx",
        "src/hooks/useWorkspaceSocket.ts",
      ],
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
