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
  "--site-on-background": "#101828",
  "--site-surface": "#ffffff",
  "--site-surface-container": "#ffffff",
  "--site-surface-container-low": "#f0f4ff",
  "--site-surface-container-high": "#e6ecff",
  "--site-surface-container-highest": "#d9e2ff",
  "--site-on-surface": "#101828",
  "--site-on-surface-variant": "#475467",
  "--site-primary": "#3155d4",
  "--site-on-primary": "#ffffff",
  "--site-primary-container": "#e1e8ff",
  "--site-on-primary-container": "#001a66",
  "--site-secondary": "#e0a931",
  "--site-cta-gradient": "linear-gradient(135deg,#3155d4,#1a3ab8)",
  "--site-outline-variant": "rgba(0,0,0,0.1)",
} as React.CSSProperties;
