import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "test-token",
    user: { role: "estudiante" },
  }),
}));

vi.mock("@/lib/site-branding", () => ({
  useSiteBranding: () => ({
    logoUrl: "",
    logoName: "",
  }),
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsThemes: vi.fn().mockResolvedValue([]),
  patchCmsTheme: vi.fn().mockResolvedValue({}),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}));

vi.mock("@/components/ui/OptimizedImage", () => ({
  default: (props: { alt?: string }) => <img alt={props.alt || "mock-image"} />,
}));

import CmsBrandingPage from "../src/app/plataforma/cms/branding/page";

describe("CmsBrandingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("disables branding save actions for read-only roles", () => {
    render(<CmsBrandingPage />);

    expect(screen.getByRole("button", { name: /guardar/i })).toBeDisabled();
    expect(screen.getByText(/solo lectura/i)).toBeTruthy();
  });
});
