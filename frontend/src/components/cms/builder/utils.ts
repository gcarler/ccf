import type React from "react";

export function safeString(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

export function asObject(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as Record<string, unknown>;
  return {};
}

/** CSS custom properties used by the canvas preview to simulate site theme. */
export const CANVAS_PREVIEW_TOKENS: React.CSSProperties = {
  "--site-background": "#f8f9ff",
  "--site-on-background": "#001b3d",
  "--site-surface": "#ffffff",
  "--site-surface-container": "#f8f9ff",
  "--site-surface-container-low": "#f0f3fa",
  "--site-surface-container-high": "#e2e7f0",
  "--site-surface-container-highest": "#d4e3ff",
  "--site-on-surface": "#001b3d",
  "--site-on-surface-variant": "#42474e",
  "--site-primary": "#004581",
  "--site-on-primary": "#ffffff",
  "--site-primary-container": "#d4e3ff",
  "--site-on-primary-container": "#001c3b",
  "--site-secondary": "#018abd",
  "--site-cta-gradient": "linear-gradient(to right, #004581, #018abd, #004581)",
  "--site-outline-variant": "rgba(0,0,0,0.1)",
} as React.CSSProperties;
